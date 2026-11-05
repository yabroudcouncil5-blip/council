from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.forms import ModelChoiceField


class SelectionOnlyRelatedFieldsMixin:
    """Related fields choose records; their own admin pages manage records."""

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if field is None:
            return field
        if isinstance(field, ModelChoiceField):
            field.empty_label = 'اختر من القائمة'
        if isinstance(field.widget, RelatedFieldWidgetWrapper):
            field.widget.can_add_related = False
            field.widget.can_change_related = False
            field.widget.can_delete_related = False
            field.widget.can_view_related = False
        return field


class SuperAdminReferenceDataMixin:
    """Department/category definitions are managed only by the super admin."""

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)
