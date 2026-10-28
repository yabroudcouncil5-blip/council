from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Page, NewsArticle, DepartmentPage, ExecutiveMember
from .forms import PageForm, NewsForm

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
    list_display = ('title', 'slug', 'published', 'updated_at')
    list_filter = ('published',)
    search_fields = ('title', 'slug', 'body')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (('محتوى الصفحة', {'fields': ('title', 'slug', 'body')}), ('إعدادات النشر', {'fields': ('published',)}))

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
