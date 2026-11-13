from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin, UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.widgets import UnfoldAdminSelectWidget

from core.models import Department
from core.admin_widgets import SuperAdminReferenceDataMixin

admin.site.unregister(User)
admin.site.unregister(Group)


ROLE_CHOICES = (
    ('staff', 'موظف قسم'),
    ('supervisor', 'مشرف قسم'),
    ('reviewer', 'مراجع واعتماد'),
    ('superadmin', 'مشرف عام'),
)


def role_field():
    return forms.ChoiceField(
        label='الدور الوظيفي', choices=ROLE_CHOICES,
        widget=UnfoldAdminSelectWidget,
        help_text='تُضبط صلاحيات الحساب تلقائياً حسب الدور.',
    )


def departments_field():
    return forms.ModelMultipleChoiceField(
        label='الأقسام', queryset=Department.objects.filter(active=True).order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='حدد القسم أو الأقسام التي يعمل فيها الموظف.',
    )


class StaffPasswordWidget(forms.Widget):
    """Offer the secure password form without exposing hash metadata in the UI."""

    template_name = 'accounts/widgets/password_summary.html'
    read_only = True

    def __init__(self, can_change_password=True, **kwargs):
        super().__init__(**kwargs)
        self.can_change_password = can_change_password

    def get_context(self, name, value, attrs):
        context = super().get_context(name, None, attrs)
        context['can_change_password'] = self.can_change_password
        return context

    def id_for_label(self, id_):
        return None


class RoleMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('username', 'email', 'password1', 'password2'):
            if name in self.fields:
                self.fields[name].widget.attrs['dir'] = 'ltr'
        if 'is_active' in self.fields:
            self.fields['is_active'].widget = forms.CheckboxInput()
            self.fields['is_active'].label = 'الحساب نشط'
            self.fields['is_active'].help_text = 'أوقف هذا الخيار لمنع الدخول دون حذف الحساب.'
        if 'username' in self.fields:
            self.fields['username'].help_text = 'اسم الدخول إلى لوحة الإدارة.'

    def clean(self):
        data = super().clean()
        if data.get('role') in {'staff', 'supervisor'} and not data.get('departments'):
            self.add_error('departments', 'حدد قسم الموظف قبل حفظ الحساب.')
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        user.is_superuser = self.cleaned_data.get('role') == 'superadmin'
        if commit:
            user.save()
            self._save_m2m()
        return user

    def _save_m2m(self):
        # Django admin saves the user with commit=False, then calls save_m2m.
        # Apply the simple role and department choices at that same save point.
        super()._save_m2m()
        group_names = {
            'staff': 'Department Officer',
            'supervisor': 'Department Manager',
            'reviewer': 'Complaint Reviewer',
        }
        role = self.cleaned_data.get('role', 'staff')
        groups = []
        if role in group_names:
            group, _ = Group.objects.get_or_create(name=group_names[role])
            groups.append(group)
        self.instance.groups.set(groups)
        # The selected role replaces previous access, including direct grants
        # that are not shown in this simplified staff form.
        self.instance.user_permissions.clear()
        self.instance.council_departments.set(self.cleaned_data.get('departments', []))


class SimpleUserCreationForm(RoleMixin, UserCreationForm):
    role = role_field()
    departments = departments_field()


class SimpleUserChangeForm(RoleMixin, UserChangeForm):
    role = role_field()
    departments = departments_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget = StaffPasswordWidget(
            can_change_password=getattr(self, 'staff_can_change_password', True),
        )
        self.fields['password'].help_text = ''
        if self.instance.is_superuser:
            self.initial['role'] = 'superadmin'
        elif self.instance.groups.filter(name='Department Officer').exists():
            self.initial['role'] = 'staff'
        elif self.instance.groups.filter(name='Complaint Reviewer').exists():
            self.initial['role'] = 'reviewer'
        elif self.instance.groups.filter(name='Department Manager').exists():
            self.initial['role'] = 'supervisor'
        else:
            self.initial['role'] = 'staff'
        self.initial['departments'] = self.instance.council_departments.filter(active=True)


@admin.register(User)
class UserAdmin(SuperAdminReferenceDataMixin, BaseUserAdmin, ModelAdmin):
    form = SimpleUserChangeForm
    add_form = SimpleUserCreationForm
    change_password_form = AdminPasswordChangeForm
    fieldsets = (
        ('بيانات الموظف', {'fields': (('first_name', 'last_name'), 'email')}),
        ('الدخول إلى النظام', {'fields': (('username', 'password'),)}),
        ('الدور والأقسام', {'fields': ('role', 'departments', 'is_active')}),
        ('سجل الحساب', {'classes': ('collapse',), 'fields': (('last_login', 'date_joined'),)}),
    )
    add_fieldsets = (
        ('بيانات الموظف', {'fields': (('first_name', 'last_name'), 'email')}),
        ('الدخول إلى النظام', {'fields': ('username', ('password1', 'password2'))}),
        ('الدور والأقسام', {'fields': ('role', 'departments', 'is_active')}),
    )
    readonly_fields = ('last_login', 'date_joined')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.staff_can_change_password = self.has_change_permission(request, obj)
        return form

    @admin.display(description='الدور الوظيفي')
    def role(self, obj):
        if obj.is_superuser:
            return dict(ROLE_CHOICES)['superadmin']
        names = set(obj.groups.values_list('name', flat=True))
        if 'Department Officer' in names:
            return dict(ROLE_CHOICES)['staff']
        if 'Complaint Reviewer' in names:
            return dict(ROLE_CHOICES)['reviewer']
        if 'Department Manager' in names:
            return dict(ROLE_CHOICES)['supervisor']
        return dict(ROLE_CHOICES)['staff']

    @admin.display(description='الأقسام')
    def departments(self, obj):
        return '، '.join(obj.council_departments.values_list('name', flat=True)) or 'لم يُحدد قسم'


@admin.register(Group)
class GroupAdmin(SuperAdminReferenceDataMixin, BaseGroupAdmin, ModelAdmin):
    pass
