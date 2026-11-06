"""The single write path for complaint stages, history and approved evidence."""
from pathlib import Path

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import Department
from .models import (
    AssignmentAction, Complaint, ComplaintAssignment, ComplaintAttachment,
    ComplaintPublication, ComplaintReview, ComplaintStatusHistory, InternalNotification,
)

TERMINAL = {'completed', 'closed'}
ACTIVE = {'assigned', 'in_progress', 'submitted', 'returned'}
ACTION_LABELS = {
    'assign': 'إحالة إلى قسم', 'start': 'بدء المعالجة',
    'submit': 'إرسال الإجراء والأدلة للمراجعة',
    'approved': 'اعتماد وإغلاق ونشر', 'closed': 'إغلاق دون معالجة ونشر السبب',
    'returned': 'إعادة إلى القسم نفسه', 'additional_assignment': 'تحويل إلى قسم آخر',
    'publish': 'نشر النتيجة والأدلة المعتمدة',
}


class WorkflowError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status
        super().__init__(message)


def can_review(user):
    return bool(user.is_active and user.is_staff and (
        user.is_superuser
        or user.groups.filter(name__in=['Complaint Reviewer', 'Department Manager']).exists()
        or user.has_perm('complaints.add_complaintreview')
    ))


def can_work(user, assignment):
    return bool(user.is_active and user.is_staff and assignment and (
        user.is_superuser or assignment.officer_id == user.pk
        or assignment.department.members.filter(pk=user.pk).exists()
    ))


def complaints_for(user):
    if not user.is_active or not user.is_staff:
        return Complaint.objects.none()
    if can_review(user):
        return Complaint.objects.all()
    return Complaint.objects.filter(
        Q(assignments__department__members=user) | Q(assignments__officer=user)
    ).distinct()


def available_actions(user, complaint):
    if can_review(user):
        if complaint.status in TERMINAL:
            return ['publish', 'additional_assignment']
        if complaint.status in {'submitted', 'under_review'}:
            return ['assign', 'closed']
        if complaint.status == 'final_review':
            return ['approved', 'returned', 'additional_assignment', 'closed']
        work = [item for item in complaint.assignments.filter(status__in=['assigned', 'returned', 'in_progress']) if can_work(user, item)]
        choices = (['start'] if any(item.status != 'in_progress' for item in work) else []) + (['submit'] if work else [])
        return choices + ['additional_assignment', 'closed']
    assignments = complaint.assignments.filter(status__in=ACTIVE).select_related('department')
    if complaint.status not in TERMINAL and any(can_work(user, item) for item in assignments):
        if assignments.filter(status='submitted').count() == assignments.count():
            return []
        return (['start'] if any(item.status in {'assigned', 'returned'} and can_work(user, item) for item in assignments) else []) + ['submit']
    return []


def _stage(complaint, status, actor, message):
    complaint.status = status
    complaint.save(update_fields=('status', 'updated_at'))
    ComplaintStatusHistory.objects.create(
        complaint=complaint, status=status, actor=actor, public_message=message,
    )


def _unpublish(complaint):
    ComplaintPublication.objects.filter(complaint=complaint).update(approved=False)


def validate_evidence(uploads):
    allowed = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
               '.webp': 'image/webp', '.pdf': 'application/pdf'}
    for upload in uploads:
        if upload.size > 5 * 1024 * 1024 or allowed.get(Path(upload.name).suffix.lower()) != upload.content_type:
            raise WorkflowError('الدليل يجب أن يكون صورة JPEG أو PNG أو WebP أو PDF وأقل من 5 ميغابايت.')


def _upload(complaint, user, uploads):
    return [ComplaintAttachment.objects.create(
        complaint=complaint, source='staff', uploaded_by=user, file=upload,
        original_name=upload.name, visibility='internal',
    ) for upload in uploads]


def _publish(complaint, user, summary, evidence_ids, uploads):
    if not summary.strip():
        raise WorkflowError('اكتب ملخصاً واضحاً للمواطن قبل الاعتماد والنشر.')
    selected = complaint.attachments.filter(pk__in=evidence_ids, source='staff')
    if selected.count() != len(set(str(pk) for pk in evidence_ids)):
        raise WorkflowError('اختر أدلة فريق البلدية الخاصة بهذه الشكوى فقط.')
    for item in selected:
        if not item.file or not item.file.storage.exists(item.file.name):
            raise WorkflowError('أحد الأدلة المختارة غير موجود في التخزين. أعد رفعه قبل النشر.')
    added = _upload(complaint, user, uploads)
    selected_ids = list(selected.values_list('pk', flat=True)) + [item.pk for item in added]
    complaint.attachments.filter(source='staff').update(visibility='internal')
    complaint.attachments.filter(pk__in=selected_ids).update(visibility='public')
    visibility = 'tracked'
    ComplaintPublication.objects.update_or_create(complaint=complaint, defaults={
        'summary': summary.strip(), 'visibility': visibility, 'approved': True,
        'approved_by': user, 'published_at': timezone.now(),
    })


@transaction.atomic
def transition(complaint_id, user, action, *, department_id=None, assignment_id=None,
               internal_note='', public_message='', evidence_ids=(), uploads=(),
               priority='medium', due_at=None, version=None, confirm=False):
    complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
    if not user.is_active or not user.is_staff:
        raise PermissionDenied
    if version and version != complaint.updated_at.isoformat():
        raise WorkflowError('تغيرت الشكوى منذ فتحها. حدّث الصفحة وراجع آخر إجراء.', 409)
    uploads = list(uploads)
    validate_evidence(uploads)
    evidence_ids = [str(pk) for pk in evidence_ids]
    if any(not pk.isdecimal() for pk in evidence_ids):
        raise WorkflowError('اختيار الأدلة غير صحيح.')
    reviewer = can_review(user)
    if action not in {'start', 'submit'} and not reviewer:
        raise PermissionDenied
    assignments = complaint.assignments.select_related('department').order_by('-assigned_at', '-pk')
    assignment = None
    if assignment_id:
        assignment = assignments.filter(pk=assignment_id).first()
        if not assignment:
            raise WorkflowError('الإحالة لا تتبع هذه الشكوى.')
    elif action in {'start', 'submit'}:
        assignment = next((item for item in assignments.filter(status__in=['assigned', 'returned', 'in_progress'])
                           if can_work(user, item)), None)
    else:
        assignment = assignments.filter(status__in=ACTIVE).first()

    if action in {'assign', 'additional_assignment'}:
        if action == 'assign' and complaint.status in TERMINAL:
            raise WorkflowError('استخدم تحويل الشكوى لإعادة فتحها.', 409)
        department = Department.objects.filter(pk=department_id, active=True).first()
        if not department:
            raise WorkflowError('اختر قسماً نشطاً لإحالة الشكوى.')
        if priority not in {'low', 'medium', 'high', 'urgent'}:
            raise WorkflowError('اختر أولوية صحيحة.')
        if isinstance(due_at, str) and due_at:
            due_at = parse_datetime(due_at)
            if due_at is None:
                raise WorkflowError('الموعد المحدد غير صحيح.')
        if due_at and timezone.is_naive(due_at):
            due_at = timezone.make_aware(due_at)
        if action == 'additional_assignment':
            if not internal_note.strip():
                raise WorkflowError('اكتب سبب تحويل الشكوى للقسم الآخر.')
            assignments.filter(status__in=ACTIVE).update(status='cancelled')
            ComplaintReview.objects.create(complaint=complaint, assignment=assignment, reviewer=user,
                                          decision=action, reason=internal_note)
        elif assignments.filter(department=department, status__in=ACTIVE).exists():
            raise WorkflowError('الشكوى محالة إلى هذا القسم بالفعل.', 409)
        assignment = ComplaintAssignment.objects.create(
            complaint=complaint, department=department, officer=None,
            priority=priority, due_at=due_at or None,
        )
        _unpublish(complaint)
        status = 'transferred' if action == 'additional_assignment' else 'assigned'
        _stage(complaint, status, user, f'تمت إحالة الشكوى إلى قسم {department.name}' +
               (' لاستكمال المعالجة' if status == 'transferred' else ''))
        for member in department.members.filter(is_active=True, is_staff=True):
            InternalNotification.objects.create(user=member, complaint=complaint,
                                                message=f'إحالة جديدة للقسم: {complaint.reference}')
    elif action in {'start', 'submit'}:
        if complaint.status in TERMINAL or not assignment or assignment.status not in {'assigned', 'returned', 'in_progress'}:
            raise WorkflowError('لا توجد إحالة مفتوحة يمكن اتخاذ إجراء عليها.', 409)
        if not can_work(user, assignment):
            raise PermissionDenied
        _unpublish(complaint)
        if action == 'start':
            if assignment.status == 'in_progress':
                raise WorkflowError('بدأت معالجة هذه الإحالة بالفعل.', 409)
            assignment.status = 'in_progress'
            assignment.save(update_fields=('status',))
            _stage(complaint, 'in_progress', user, f'بدأ قسم {assignment.department.name} معالجة الشكوى')
        else:
            if not internal_note.strip():
                raise WorkflowError('سجّل الإجراء المتخذ قبل إرساله للمراجعة.')
            AssignmentAction.objects.create(assignment=assignment, actor=user,
                                           internal_action=internal_note, public_message=public_message)
            _upload(complaint, user, uploads)
            assignment.status = 'submitted'
            assignment.save(update_fields=('status',))
            pending_work = assignments.exclude(pk=assignment.pk).filter(status__in=['assigned', 'returned', 'in_progress']).exists()
            _stage(complaint, 'in_progress' if pending_work else 'final_review', user,
                   'تم تسجيل إجراء القسم، وتستكمل الأقسام الأخرى العمل' if pending_work else 'تم اتخاذ الإجراء وإرسال الشكوى للمراجعة النهائية')
            reviewers = user.__class__.objects.filter(is_active=True, is_staff=True).filter(
                Q(is_superuser=True) | Q(groups__name__in=['Complaint Reviewer', 'Department Manager'])
            ).distinct()
            for reviewer_user in reviewers:
                InternalNotification.objects.create(user=reviewer_user, complaint=complaint,
                                                    message=f'إجراء وأدلة بانتظار المراجعة: {complaint.reference}')
    elif action == 'returned':
        if not assignment or assignment.status != 'submitted':
            raise WorkflowError('لا توجد معالجة مقدمة للمراجعة لإعادتها.', 409)
        if not internal_note.strip():
            raise WorkflowError('اكتب المطلوب من القسم لاستكمال المعالجة.')
        ComplaintReview.objects.create(complaint=complaint, assignment=assignment, reviewer=user,
                                      decision='returned', reason=internal_note)
        assignment.status = 'returned'
        assignment.save(update_fields=('status',))
        _unpublish(complaint)
        _stage(complaint, 'assigned', user, f'أعيدت الشكوى إلى قسم {assignment.department.name} لاستكمال المعالجة')
    elif action in {'approved', 'closed'}:
        if not confirm:
            raise WorkflowError('أكد مراجعة الإجراء والأدلة قبل اعتماد القرار.')
        if complaint.status in TERMINAL:
            raise WorkflowError('صدر قرار نهائي بالفعل. استخدم نشر النتيجة أو تحويل الشكوى.', 409)
        if not public_message.strip():
            raise WorkflowError('اكتب النتيجة التي ستظهر للمواطن.')
        if action == 'approved':
            if not assignment or assignment.status != 'submitted' or not assignment.actions.exists():
                raise WorkflowError('يجب أن يرسل القسم الإجراء للمراجعة قبل اعتماده.', 409)
            assignment.status = 'approved'
            assignment.save(update_fields=('status',))
            if assignments.filter(status__in=ACTIVE).exists():
                _upload(complaint, user, uploads)
                ComplaintReview.objects.create(complaint=complaint, assignment=assignment, reviewer=user,
                                              decision=action, reason=internal_note)
                waiting = assignments.filter(status__in=['assigned', 'returned', 'in_progress']).exists()
                _stage(complaint, 'in_progress' if waiting else 'final_review', user,
                       'تمت مراجعة إجراء أحد الأقسام، وتستكمل متابعة باقي الإحالات')
                return complaint, assignment
        else:
            assignments.filter(status__in=ACTIVE).update(status='cancelled')
        ComplaintReview.objects.create(complaint=complaint, assignment=assignment, reviewer=user,
                                      decision=action, reason=internal_note)
        _publish(complaint, user, public_message, evidence_ids, uploads)
        _stage(complaint, 'completed' if action == 'approved' else 'closed', user, public_message.strip())
    elif action == 'publish':
        if complaint.status not in TERMINAL or not confirm:
            raise WorkflowError('راجع القرار النهائي وأكد النشر أولاً.', 409)
        _publish(complaint, user, public_message, evidence_ids, uploads)
        _stage(complaint, complaint.status, user, public_message.strip())
    else:
        raise WorkflowError('اختر إجراءً صحيحاً.')
    return complaint, assignment
