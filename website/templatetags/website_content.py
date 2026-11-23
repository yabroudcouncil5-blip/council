import re
from html import unescape

from django import template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from website.richtext import content_html

register = template.Library()


@register.filter
def rich_content(value):
    return mark_safe(content_html(value))


@register.filter
def plain_content(value):
    """Prepare rich editor content for an auto-escaped, word-wrapped excerpt."""
    content = re.sub(r'<(?:br\s*/?|/(?:p|div|h[23]|li|blockquote))>', ' ', content_html(value))
    text = unescape(strip_tags(content))
    return ' '.join(text.replace('&nbsp;', ' ').split())


@register.filter
def news_content(value):
    content = content_html(value)
    # Keep HTML attributes intact while making editor-inserted spaces wrap in prose.
    content = re.sub(r'(<[^>]*>)|&nbsp;|\u00a0', lambda match: match[1] or ' ', content)
    return mark_safe(content)
