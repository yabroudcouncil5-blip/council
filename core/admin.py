from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import CouncilSettings, Department, ComplaintCategory, AuditLog

@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(ModelAdmin):
    list_display = ('name', 'default_days', 'active')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ('name', 'active')
    list_filter = ('active',)
    search_fields = ('name',)
    filter_horizontal = ('members',)

@admin.register(CouncilSettings)
class CouncilSettingsAdmin(ModelAdmin):
    list_display = ('name', 'phone', 'email', 'updated_at')
    fieldsets = (
        ('بيانات البلدية', {'fields': ('name', 'logo', 'description')}),
        ('بيانات التواصل', {'fields': ('address', 'phone', 'email', 'facebook_url')}),
    )

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ('action', 'target_type', 'target_id', 'actor', 'created_at')
    list_filter = ('action',)
    search_fields = ('action', 'target_type', 'target_id')
    readonly_fields = ('created_at',)

# Register your models here.
