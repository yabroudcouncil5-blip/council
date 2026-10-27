from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from complaints.models import Complaint, ComplaintAssignment, InternalNotification
from core.models import Department


def dashboard_callback(request, context):
    """Build the council work overview using the user's model permissions."""
    can_view = request.user.has_perm('complaints.view_complaint')
    can_assign = request.user.has_perm('complaints.view_complaintassignment')
    counts = dict(Complaint.objects.values_list('status').annotate(total=Count('id'))) if can_view else {}
    total = sum(counts.values())
    now = timezone.now()
    overdue = ComplaintAssignment.objects.filter(due_at__lt=now).exclude(status__in=['approved', 'cancelled'])
    context.update({
        'dashboard_date': now,
        'metrics': [
            {'title': 'إجمالي الشكاوى', 'value': total, 'icon': 'inbox', 'link': reverse('admin:complaints_complaint_changelist')},
            {'title': 'بانتظار المراجعة', 'value': counts.get('submitted', 0) + counts.get('under_review', 0), 'icon': 'pending_actions', 'link': reverse('admin:complaints_complaint_changelist') + '?status__in=submitted,under_review'},
            {'title': 'قيد المعالجة', 'value': sum(counts.get(s, 0) for s in ['assigned', 'in_progress', 'final_review']), 'icon': 'engineering', 'link': reverse('admin:complaints_complaint_changelist') + '?status__in=assigned,in_progress,final_review'},
            {'title': 'تمت المعالجة', 'value': counts.get('completed', 0), 'icon': 'task_alt', 'link': reverse('admin:complaints_complaint_changelist') + '?status__exact=completed'},
        ] if can_view else [],
        'status_rows': [{'label': label, 'count': counts.get(status, 0), 'percent': round(counts.get(status, 0) * 100 / total) if total else 0} for status, label in Complaint.STATUS] if can_view else [],
        'recent_complaints': Complaint.objects.select_related('category').order_by('-submitted_at')[:6] if can_view else [],
        'overdue_count': overdue.count() if can_assign else None,
        'overdue_tasks': overdue.select_related('complaint', 'department').order_by('due_at')[:5] if can_assign else [],
        'department_count': Department.objects.filter(active=True).count() if request.user.has_perm('core.view_department') else None,
        'notifications': InternalNotification.objects.filter(user=request.user, read=False).order_by('-created_at')[:4],
        'completion_rate': round(counts.get('completed', 0) * 100 / total) if total else 0,
        'can_view_complaints': can_view,
        'can_view_assignments': can_assign,
    })
    return context
