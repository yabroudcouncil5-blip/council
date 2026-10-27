import re

import nh3
from django.utils.html import escape, linebreaks

TAGS = {'p', 'br', 'h2', 'h3', 'strong', 'b', 'em', 'i', 'u', 's', 'blockquote', 'ol', 'ul', 'li', 'a', 'img', 'span', 'div'}
CLASSES = {'ql-align-left', 'ql-align-center', 'ql-align-right', 'ql-align-justify', 'ql-direction-rtl'}


def attribute_filter(tag, attribute, value):
    if tag == 'img' and attribute == 'src':
        # Only images uploaded through the council's editor can be embedded.
        return value if re.fullmatch(r'/website-images/[a-f0-9]{32}\.webp', value) else None
    if attribute == 'style':
        # Only the editor's predefined font sizes; no arbitrary layout overrides.
        sizes = re.findall(r'(?:^|;)\s*font-size\s*:\s*(14|16|18|24|32|40)px\s*(?:;|$)', value)
        return 'font-size: ' + sizes[-1] + 'px' if sizes else None
    return value


def sanitize_html(value):
    return nh3.clean(
        value or '', tags=TAGS,
        attributes={'a': {'href', 'title'}, 'img': {'src', 'alt'}, '*': {'style', 'dir'}},
        allowed_classes={tag: CLASSES for tag in TAGS},
        attribute_filter=attribute_filter,
        url_schemes={'http', 'https', 'mailto', 'tel'},
        filter_style_properties={'font-size'},
    )


def content_html(value):
    value = value or ''
    # Existing plain-text pages retain paragraphs and literal angle brackets.
    if not re.search(r'</?(?:p|h[23]|strong|b|em|i|u|s|blockquote|ol|ul|li|a|img|span|div|br)(?:\s|/?>)', value, re.I):
        return linebreaks(escape(value))
    return sanitize_html(value)
