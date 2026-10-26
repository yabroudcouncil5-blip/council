from django.contrib import admin
from .models import CouncilSettings, Department, ComplaintCategory, AuditLog

@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_days', 'active')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    list_filter = ('active',)
    search_fields = ('name',)

@admin.register(CouncilSettings)
class CouncilSettingsAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'updated_at')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'target_type', 'target_id', 'actor', 'created_at')
    list_filter = ('action',)
    search_fields = ('action', 'target_type', 'target_id')
    readonly_fields = ('created_at',)

# Register your models here.
