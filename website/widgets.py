from django import forms

from .richtext import content_html


class PageEditor(forms.Textarea):
    template_name = 'website/widgets/editor.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['editor_html'] = content_html(value)
        return context

    class Media:
        css = {'all': ('website/vendor/quill/quill.snow.css', 'website/editor.css')}
        js = ('website/vendor/quill/quill.js', 'website/editor.js')
