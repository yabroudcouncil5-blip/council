from datetime import timedelta
from django.db import migrations, models


def reconcile(apps, schema_editor):
    """Repair old record-only admin saves without publishing private notes/files."""
    Complaint = apps.get_model('complaints', 'Complaint')
    History = apps.get_model('complaints', 'ComplaintStatusHistory')
    Attachment = apps.get_model('complaints', 'ComplaintAttachment')
    Review = apps.get_model('complaints', 'ComplaintReview')
    Assignment = apps.get_model('complaints', 'ComplaintAssignment')
    Action = apps.get_model('complaints', 'AssignmentAction')
    Publication = apps.get_model('complaints', 'ComplaintPublication')
    alias = schema_editor.connection.alias
    Attachment.objects.using(alias).filter(uploaded_by__is_staff=True).update(source='staff')
    messages = {
        'submitted': 'تم استلام الشكوى', 'assigned': 'تمت إحالة الشكوى إلى القسم المختص',
        'in_progress': 'بدأ القسم المختص معالجة الشكوى',
        'final_review': 'تم اتخاذ الإجراء وإرساله للمراجعة النهائية',
        'transferred': 'أحيلت الشكوى إلى قسم آخر لاستكمال المعالجة',
        'completed': 'تم اعتماد المعالجة وإغلاق الشكوى', 'closed': 'أغلقت الشكوى دون معالجة',
    }
    for complaint in Complaint.objects.using(alias).iterator():
        assignments = Assignment.objects.using(alias).filter(complaint_id=complaint.pk)
        latest_assignment = assignments.order_by('-assigned_at', '-pk').first()
        review = Review.objects.using(alias).filter(complaint_id=complaint.pk).order_by('-created_at', '-pk').first()
        action = Action.objects.using(alias).filter(assignment__complaint_id=complaint.pk).order_by('-created_at', '-pk').first()
        latest_history = History.objects.using(alias).filter(complaint_id=complaint.pk).order_by('-created_at', '-pk').first()
        status = complaint.status
        actor_id = None
        # A later routing/action/history event starts a new cycle and must not
        # be overwritten by a decision from the previous department/cycle.
        review_is_latest = review and not any(
            at and at > review.created_at + timedelta(seconds=2)
            for at in (latest_assignment.assigned_at if latest_assignment else None,
                       action.created_at if action else None,
                       latest_history.created_at if latest_history and latest_history.status not in {'completed', 'closed'} else None)
        )
        if review_is_latest:
            actor_id = review.reviewer_id
            target = assignments.filter(pk=review.assignment_id).first() if review.assignment_id else latest_assignment
            if review.decision == 'approved':
                if target:
                    assignments.filter(pk=target.pk).update(status='approved')
                if not assignments.exclude(status__in=['approved', 'cancelled']).exists():
                    status = 'completed'
            elif review.decision == 'closed':
                # The old "closed" action meant close-without-publication,
                # not necessarily close-without-repair. Preserve completed
                # cases with a recorded staff action rather than relabelling
                # their successful repair as unprocessed.
                status = 'completed' if action and complaint.status != 'closed' else 'closed'
                assignments.exclude(status__in=['approved', 'cancelled']).update(status='cancelled')
            elif review.decision == 'returned':
                status = 'assigned'
                if target:
                    assignments.filter(pk=target.pk).update(status='returned')
            elif review.decision == 'additional_assignment':
                status = 'transferred'
        elif status not in {'completed', 'closed'} and latest_assignment:
            if action and action.created_at >= latest_assignment.assigned_at:
                status = 'final_review'
            else:
                status = {'assigned': 'assigned', 'returned': 'assigned', 'in_progress': 'in_progress',
                          'submitted': 'final_review'}.get(latest_assignment.status, status)
        if status != complaint.status:
            Complaint.objects.using(alias).filter(pk=complaint.pk).update(status=status)
        if status not in {'completed', 'closed'}:
            Publication.objects.using(alias).filter(complaint_id=complaint.pk).update(approved=False)
        if not History.objects.using(alias).filter(complaint_id=complaint.pk, status='submitted').exists():
            event = History.objects.using(alias).create(complaint_id=complaint.pk, status='submitted', public_message=messages['submitted'])
            History.objects.using(alias).filter(pk=event.pk).update(created_at=complaint.submitted_at)
        if not latest_history or latest_history.status != status:
            event = History.objects.using(alias).create(complaint_id=complaint.pk, status=status,
                                                        actor_id=actor_id, public_message=messages.get(status, 'تم تحديث مرحلة الشكوى'))
            if review_is_latest:
                History.objects.using(alias).filter(pk=event.pk).update(created_at=review.created_at)


class Migration(migrations.Migration):
    dependencies = [('complaints', '0007_complaintattachment_source_and_more')]
    operations = [
        migrations.AlterField(model_name='complaintreview', name='decision',
            field=models.CharField(choices=[('returned', 'إعادة للقسم'), ('additional_assignment', 'إحالة إلى قسم آخر'),
                                           ('approved', 'اعتماد وإغلاق ونشر'), ('closed', 'إغلاق دون معالجة')],
                                   max_length=30, verbose_name='قرار المراجعة')),
        migrations.RunPython(reconcile, migrations.RunPython.noop),
    ]
