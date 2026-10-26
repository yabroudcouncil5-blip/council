from django.contrib import admin
from .models import Page, NewsArticle, DepartmentPage

@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'published', 'published_at', 'created_at')
    list_filter = ('published',)
    search_fields = ('title', 'body')

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'published', 'updated_at')
    list_filter = ('published',)
    search_fields = ('title', 'slug', 'body')

@admin.register(DepartmentPage)
class DepartmentPageAdmin(admin.ModelAdmin):
    list_display = ('name', 'published', 'contact')
    list_filter = ('published',)
    search_fields = ('name', 'description')
