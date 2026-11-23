from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncWeek
from django.utils import timezone

from complaints.models import Complaint


def chart_rows(pairs):
    maximum = max((count for _, count in pairs), default=0)
    if not maximum:
        return []
    return [{'label': label, 'count': count, 'max': maximum,
             'percent': round(count * 100 / maximum, 2)} for label, count in pairs]


def complaint_charts(visible, counts, overdue, now):
    today = timezone.localdate(now)
    first_week = today - timedelta(days=today.weekday(), weeks=7)
    weekly_counts = {
        week.date(): count
        for week, count in visible.filter(submitted_at__date__gte=first_week, submitted_at__lte=now)
        .annotate(week=TruncWeek('submitted_at')).values_list('week').annotate(total=Count('pk')).order_by('week')
    }
    weeks = [first_week + timedelta(weeks=index) for index in range(8)]
    department_counts = list(overdue.values_list('department__name').annotate(
        total=Count('pk'),
    ).order_by('-total', 'department__name')[:8])
    return [
        {'title': 'الشكاوى الواردة أسبوعياً', 'variant': 'weekly',
         'caption': 'آخر ٨ أسابيع · التاريخ يشير إلى بداية الأسبوع',
         'rows': chart_rows([(week.strftime('%d/%m'), weekly_counts.get(week, 0)) for week in weeks])},
        {'title': 'الشكاوى حسب الحالة', 'variant': 'status',
         'caption': 'عدد الشكاوى في كل حالة',
         'rows': chart_rows([(label, counts.get(status, 0)) for status, label in Complaint.STATUS])},
        {'title': 'الإحالات المتأخرة حسب القسم', 'variant': 'overdue',
         'caption': 'الأقسام الثمانية الأعلى عدداً في الإحالات المتأخرة',
         'rows': chart_rows(department_counts)},
    ]
