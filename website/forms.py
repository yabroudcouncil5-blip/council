from django import forms

from .models import Page, NewsArticle
from .richtext import sanitize_html
from .widgets import PageEditor


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = '__all__'
        widgets = {'body': PageEditor}
        labels = {'title': 'عنوان الصفحة'}
        help_texts = {'body': 'اكتب المحتوى، وحدد النص لتغيير حجمه أو تنسيقه. استخدم زر الصورة لرفع صورة من جهازك.'}

    def clean_body(self):
        return sanitize_html(self.cleaned_data['body'])


class NewsForm(PageForm):
    featured_image = forms.ImageField(label='الصورة الرئيسية', required=False)

    def clean_featured_image(self):
        image = self.cleaned_data['featured_image']
        if getattr(getattr(image, 'image', None), 'format', None) not in {
            None, 'JPEG', 'PNG', 'WEBP', 'GIF',
        }:
            raise forms.ValidationError('اختر صورة بصيغة JPEG أو PNG أو WebP أو GIF.')
        return image

    class Meta(PageForm.Meta):
        model = NewsArticle
        labels = {'title': 'عنوان الخبر أو الإعلان'}
