from datetime import timedelta
from pathlib import Path

from django.urls import reverse
from .models import Complaint


PUBLIC_MESSAGES = {
    'submitted': 'تم استلام الشكوى',
    'under_review': 'تجري مراجعة الشكوى لتحديد القسم المختص',
    'assigned': 'تمت إحالة الشكوى إلى القسم المختص',
    'in_progress': 'يعمل القسم المختص على معالجة الشكوى',
    'final_review': 'تم اتخاذ الإجراء وإرساله للمراجعة النهائية',
    'transferred': 'أحيلت الشكوى إلى قسم آخر لاستكمال المعالجة',
    'completed': 'تم اعتماد المعالجة وإغلاق الشكوى',
    'closed': 'أغلقت الشكوى دون معالجة',
}


def tracking_result(data):
    reference = data.get('reference', '').strip().translate(
        str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹–—', '01234567890123456789--')
    ).upper()
    complaint = Complaint.objects.filter(reference=reference).first()
    if not complaint:
        return None
    labels = dict(Complaint.STATUS)
    publication = getattr(complaint, 'publication', None)
    published = bool(complaint.status in {'completed', 'closed'} and publication
                     and publication.approved and publication.visibility in {'tracked', 'public'})
    events = []
    for item in complaint.status_history.order_by('created_at', 'pk'):
        # Old versions copied return reasons into public history. Display the
        # stage generically; only the explicitly approved summary is public.
        message = item.public_message if item.status == 'submitted' else PUBLIC_MESSAGES.get(item.status, 'تم تحديث الشكوى')
        events.append({'code': item.status, 'public_message': message, 'created_at': item.created_at})
    if not any(item['code'] == 'submitted' for item in events):
        events.insert(0, {'code': 'submitted', 'public_message': PUBLIC_MESSAGES['submitted'], 'created_at': complaint.submitted_at})

    def add_missing(code, at, message, equivalent=()):
        if not any(event['code'] in (code, *equivalent) and abs(event['created_at'] - at) < timedelta(seconds=2) for event in events):
            events.append({'code': code, 'public_message': message, 'created_at': at})

    # Include legacy records whose old admin form failed to write history.
    for assignment in complaint.assignments.select_related('department').order_by('assigned_at', 'pk'):
        add_missing('assigned', assignment.assigned_at,
                    f'تمت إحالة الشكوى إلى قسم {assignment.department.name}', equivalent=('transferred',))
        for action in assignment.actions.filter(kind='submission').order_by('created_at', 'pk'):
            add_missing('final_review', action.created_at, PUBLIC_MESSAGES['final_review'], equivalent=('in_progress',))
    for review in complaint.reviews.order_by('created_at', 'pk'):
        code = {'returned': 'assigned', 'additional_assignment': 'transferred', 'closed': 'closed'}.get(review.decision)
        if code:
            add_missing(code, review.created_at, PUBLIC_MESSAGES[code])
    events.sort(key=lambda event: event['created_at'])
    if events[-1]['code'] != complaint.status:
        events.append({'code': complaint.status, 'created_at': max(complaint.updated_at, events[-1]['created_at']),
                       'public_message': PUBLIC_MESSAGES.get(complaint.status, 'تم تحديث الشكوى')})
    if published:
        events[-1]['public_message'] = publication.summary or PUBLIC_MESSAGES[complaint.status]
    result = {
        'reference': complaint.reference, 'status': complaint.get_status_display(),
        'status_code': complaint.status, 'submitted_at': complaint.submitted_at.isoformat(),
        'timeline': [
            {'status': labels.get(item['code'], 'تحديث الحالة'), 'status_code': item['code'],
             'public_message': item['public_message'], 'created_at': item['created_at'],
             'latest': index == len(events) - 1}
            for index, item in enumerate(events)
        ],
    }
    if published and publication.published_at:
        evidence = []
        for item in complaint.attachments.filter(source='staff', visibility__in=['tracked', 'public'],
                                                 uploaded_at__lte=publication.published_at).order_by('uploaded_at', 'pk'):
            if item.file:
                suffix = Path(item.file.name).suffix.lower()
                evidence.append({'url': reverse('complaint-evidence', args=[item.pk]),
                                 'preview_url': reverse('complaint-evidence', args=[item.pk]) + '?preview=1',
                                 'name': item.original_name, 'image': suffix in {'.jpg', '.jpeg', '.png', '.webp', '.gif'},
                                 'pdf': suffix == '.pdf'})
        if evidence:
            result['evidence'] = [item['url'] for item in evidence]
            result['evidence_items'] = evidence
    return result


def tracking_context(data):
    context = {'tracking_values': data}
    if 'reference' in data:
        context['tracking_result'] = tracking_result(data)
        if not context['tracking_result']:
            context['tracking_error'] = 'لم نعثر على شكوى بهذا الرقم. تأكد من الرقم المرجعي الذي حصلت عليه عند إرسال الشكوى، أو تواصل مع البلدية للمساعدة.'
    return context
