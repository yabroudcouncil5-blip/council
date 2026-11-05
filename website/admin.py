from django.contrib import admin
from django import forms
from django.core.files.base import ContentFile
from django.utils.html import format_html
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import uuid
from unfold.admin import ModelAdmin
from .models import Page, NewsArticle, DepartmentPage, ExecutiveMember, ContentImage
from .forms import PageForm, NewsForm


class CompressedImageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].required = False

    def clean_image(self):
        upload = self.cleaned_data.get('image')
        if not upload:
            return upload
        try:
            image = Image.open(upload)
            if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise forms.ValidationError('ارفع صورة PNG أو JPEG أو WebP فقط.')
            image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.convert('RGBA' if 'A' in image.getbands() else 'RGB').save(output, 'WEBP', quality=84, method=6)
            return ContentFile(output.getvalue(), name=uuid.uuid4().hex + '.webp')
        except (UnidentifiedImageError, OSError):
            raise forms.ValidationError('تعذر قراءة الصورة. اختر صورة سليمة.')


@admin.register(ContentImage)
class ContentImageAdmin(admin.ModelAdmin):
    form = CompressedImageForm
    list_display = ('preview', 'image', 'created_at')
    readonly_fields = ('current_preview', 'created_at')
    fields = ('current_preview', 'image', 'created_at')

    @admin.display(description='الصورة الحالية')
    def preview(self, obj):
        if not obj or not obj.image:
            return '—'
        return format_html('<img src="{}" alt="" style="width:120px;height:80px;object-fit:cover;border-radius:8px">', obj.image.url)

    @admin.display(description='معاينة الصورة الحالية')
    def current_preview(self, obj):
        return self.preview(obj)

@admin.register(NewsArticle)
class NewsArticleAdmin(ModelAdmin):
    form = NewsForm
    list_display = ('title', 'published', 'published_at', 'created_at')
    list_filter = ('published',)
    search_fields = ('title', 'body')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('محتوى الخبر', {'fields': ('title', 'body', 'featured_image')}),
        ('النشر', {'fields': ('published', 'published_at', 'created_at')}),
    )

@admin.register(Page)
class PageAdmin(ModelAdmin):
    form = PageForm
    list_display = ('title', 'slug', 'published', 'updated_at', 'view_page')
    list_filter = ('published',)
    search_fields = ('title', 'slug', 'body')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (('محتوى الصفحة', {'fields': ('title', 'slug', 'body')}), ('إعدادات النشر', {'fields': ('published',)}))

    @admin.display(description='عرض الصفحة')
    def view_page(self, obj):
        from django.utils.html import format_html
        return format_html('<a href="{}" target="_blank" rel="noopener">فتح الموقع ↗</a>', obj.get_absolute_url())

@admin.register(DepartmentPage)
class DepartmentPageAdmin(ModelAdmin):
    list_display = ('name', 'published', 'contact')
    list_filter = ('published',)
    search_fields = ('name', 'description')

@admin.register(ExecutiveMember)
class ExecutiveMemberAdmin(ModelAdmin):
    list_display = ('name', 'role', 'display_order', 'active')
    list_filter = ('active',)
    search_fields = ('name', 'role', 'bio')
    list_editable = ('display_order', 'active')
    fieldsets = (
        ('بيانات العضو', {'fields': ('name', 'role', 'bio', 'photo')}),
        ('العرض', {'fields': ('display_order', 'active')}),
    )
