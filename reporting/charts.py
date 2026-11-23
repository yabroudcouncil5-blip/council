from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncWeek
from django.utils import timezone

from complaints.models import Complaint


DEPARTMENT_SERIES = [
    {'key': 'total', 'label': 'إجمالي الإحالات'},
    {'key': 'approved', 'label': 'المعتمدة'},
    {'key': 'overdue', 'label': 'المتأخرة'},
]


def count_ticks(maximum):
    target_step = max(1, (maximum + 4) // 5)
    magnitude = 10 ** (len(str(target_step)) - 1)
    step = next(magnitude * factor for factor in (1, 2, 5, 10) if magnitude * factor >= target_step)
    end = max(step, ((maximum + step - 1) // step) * step)
    return list(range(0, end + 1, step))


def count_chart(title, variant, caption, pairs, *, show_zero=False, show_share=False):
    total = sum(count for _, count in pairs)
    plotted = [(label, count) for label, count in pairs if count or show_zero]
    ticks = count_ticks(max((count for _, count in plotted), default=0))
    maximum = (total or 1) if show_share else ticks[-1]
    rows = [
        {'label': label, 'count': count, 'max': maximum,
         'percent': round(100 * count / maximum, 4),
         'share': round(100 * count / total) if show_share and total else None}
        for label, count in plotted
    ]
    return {'title': title, 'variant': variant, 'caption': caption, 'rows': rows, 'ticks': ticks}


def complaint_overview_charts(visible, counts, now):
    today = timezone.localdate(now)
    first_week = today - timedelta(days=today.weekday(), weeks=7)
    weekly_counts = {
        week.date(): count
        for week, count in visible.filter(submitted_at__date__gte=first_week, submitted_at__lte=now)
        .annotate(week=TruncWeek('submitted_at')).values_list('week').annotate(total=Count('pk')).order_by('week')
    }
    weeks = [first_week + timedelta(weeks=index) for index in range(8)]
    weekly = count_chart(
        'الشكاوى الواردة أسبوعياً', 'weekly', 'آخر ٨ أسابيع · التاريخ يشير إلى بداية الأسبوع',
        [(week.strftime('%d/%m'), weekly_counts.get(week, 0)) for week in weeks], show_zero=True,
    )
    for row, week in zip(weekly['rows'], weeks):
        row['week'] = week

    return [
        weekly,
        count_chart(
            'الشكاوى حسب الحالة', 'status', 'العدد والنسبة من إجمالي الشكاوى',
            [(label, counts.get(status, 0)) for status, label in Complaint.STATUS], show_share=True,
        ),
    ]


def complaint_charts(visible, counts, overdue, now):
    department_counts = list(overdue.values_list('department__name').annotate(
        total=Count('pk'),
    ).order_by('-total', 'department__name')[:8])
    return [
        *complaint_overview_charts(visible, counts, now),
        count_chart(
            'الإحالات المتأخرة حسب القسم', 'overdue',
            'حتى ثمانية أقسام مرتبة حسب عدد الإحالات المتأخرة', department_counts,
        ),
    ]


def report_charts(visible, counts, assignment_rows, departments, now):
    ranked = [department for department in departments if department.total][:8]
    ticks = count_ticks(max((department.total for department in ranked), default=0))
    maximum = ticks[-1]
    department_chart = {
        'title': 'الإحالات حسب القسم', 'variant': 'departments',
        'caption': 'حتى ثمانية أقسام مرتبة حسب إجمالي الإحالات',
        'series': DEPARTMENT_SERIES, 'ticks': ticks, 'rows': [
            {
                'label': department.name,
                'segments': [
                    {**series, 'count': getattr(department, series['key']),
                     'percent': round(100 * getattr(department, series['key']) / maximum, 4)}
                    for series in DEPARTMENT_SERIES
                ],
            }
            for department in ranked
        ],
    }
    return [
        *complaint_overview_charts(visible, counts, now),
        count_chart(
            'حالات الإحالات', 'assignment', 'العدد والنسبة من إجمالي الإحالات',
            [(row['label'], row['count']) for row in assignment_rows], show_share=True,
        ),
        department_chart,
    ]
