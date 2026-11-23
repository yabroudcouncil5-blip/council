from math import ceil

from django.utils import timezone
from django.utils.html import format_html


def deadline_badge(deadline, now):
    seconds_remaining = (deadline - now).total_seconds()
    overdue = seconds_remaining < 0
    days = ceil(abs(seconds_remaining) / 86_400)
    local_deadline = timezone.localtime(deadline)
    return format_html(
        '<time class="followup-badge followup-badge--{} followup-deadline" datetime="{}" title="{}">'
        '<bdi>{}</bdi> {}</time>',
        'late' if overdue else 'on-time',
        local_deadline.isoformat(),
        local_deadline.strftime('%Y/%m/%d %H:%M'),
        days,
        'متأخرة' if overdue else 'متبقٍ',
    )
