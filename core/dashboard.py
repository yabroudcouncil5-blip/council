from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from complaints.models import Complaint
from core.models import Department
from complaints.workflow import assignments_for, can_review, complaints_for, notifications_for


def dashboard_callback(request, context):
    """Build the council work overview using the user's model permissions."""
    can_view = can_review(request.user) or complaints_for(request.user).exists()
    can_assign = can_review(request.user)
    visible = complaints_for(request.user)
    counts = dict(visible.values_list('status').annotate(total=Count('id'))) if can_view else {}
    total = sum(counts.values())
    now = timezone.now()
    overdue = assignments_for(request.user).filter(due_at__lt=now).exclude(status__in=['approved', 'cancelled'])
    context.update({
        'dashboard_date': now,
        'metrics': [
            {'title': 'إجمالي الشكاوى', 'value': total, 'icon': 'inbox', 'link': reverse('admin:complaints_complaint_changelist')},
            {'title': 'بانتظار المراجعة', 'value': counts.get('final_review', 0), 'icon': 'pending_actions', 'link': reverse('admin:complaints_complaint_changelist') + '?status__exact=final_review'},
            {'title': 'قيد المتابعة', 'value': sum(counts.get(s, 0) for s in ['submitted', 'under_review', 'assigned', 'in_progress', 'transferred']), 'icon': 'engineering', 'link': reverse('admin:complaints_complaint_changelist') + '?status__in=submitted,under_review,assigned,in_progress,transferred'},
            {'title': 'تمت المعالجة', 'value': counts.get('completed', 0), 'icon': 'task_alt', 'link': reverse('admin:complaints_complaint_changelist') + '?status__exact=completed'},
        ] if can_view else [],
        'status_rows': [{'label': label, 'count': counts.get(status, 0), 'percent': round(counts.get(status, 0) * 100 / total) if total else 0} for status, label in Complaint.STATUS] if can_view else [],
        'recent_complaints': visible.select_related('category').order_by('-updated_at')[:6] if can_view else [],
        'overdue_count': overdue.count() if can_assign else None,
        'overdue_tasks': overdue.select_related('complaint', 'department').order_by('due_at')[:5] if can_assign else [],
        'department_count': Department.objects.filter(active=True).count() if request.user.has_perm('core.view_department') else None,
        'notifications': notifications_for(request.user).filter(read=False).order_by('-created_at')[:4],
        'completion_rate': round(counts.get('completed', 0) * 100 / total) if total else 0,
        'can_view_complaints': can_view,
        'can_view_assignments': can_assign,
    })
    return context
