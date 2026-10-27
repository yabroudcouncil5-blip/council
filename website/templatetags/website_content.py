from django import template
from django.utils.safestring import mark_safe

from website.richtext import content_html

register = template.Library()


@register.filter
def rich_content(value):
    return mark_safe(content_html(value))
