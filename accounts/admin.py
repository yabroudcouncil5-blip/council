from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from django import forms

admin.site.unregister(User)
admin.site.unregister(Group)


ROLE_CHOICES = (
    ('staff', 'موظف قسم'),
    ('supervisor', 'مشرف قسم'),
    ('reviewer', 'مراجع واعتماد'),
    ('superadmin', 'مشرف عام'),
)

class RoleMixin:
    role = forms.ChoiceField(label='الدور الوظيفي', choices=ROLE_CHOICES, help_text='اختر دوراً واحداً فقط؛ سيتم ضبط الصلاحيات تلقائياً.')

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            self.apply_role(user)
        return user

    def apply_role(self, user):
        role = self.cleaned_data.get('role', 'staff')
        user.is_staff = True
        user.is_superuser = role == 'superadmin'
        user.save(update_fields=['is_staff', 'is_superuser'])
        group_names = {'staff': 'Department Officer', 'supervisor': 'Department Manager', 'reviewer': 'Complaint Reviewer'}
        user.groups.clear()
        if role in group_names:
            group, _ = Group.objects.get_or_create(name=group_names[role])
            user.groups.add(group)

class SimpleUserCreationForm(RoleMixin, UserCreationForm):
    role = forms.ChoiceField(label='الدور الوظيفي', choices=ROLE_CHOICES, help_text='اختر دوراً واحداً فقط؛ سيتم ضبط الصلاحيات تلقائياً.')

class SimpleUserChangeForm(RoleMixin, UserChangeForm):
    role = forms.ChoiceField(label='الدور الوظيفي', choices=ROLE_CHOICES, help_text='اختر دوراً واحداً فقط؛ سيتم ضبط الصلاحيات تلقائياً.')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.is_superuser: self.initial['role'] = 'superadmin'
        elif self.instance.groups.filter(name='Complaint Reviewer').exists(): self.initial['role'] = 'reviewer'
        elif self.instance.groups.filter(name='Department Manager').exists(): self.initial['role'] = 'supervisor'
        else: self.initial['role'] = 'staff'

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = SimpleUserChangeForm
    add_form = SimpleUserCreationForm
    change_password_form = AdminPasswordChangeForm
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('بيانات الموظف', {'fields': ('first_name', 'last_name', 'email', 'role', 'is_active')}),
        ('التواريخ', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'email', 'role', 'is_active')}),
    )
    readonly_fields = ('last_login', 'date_joined')


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
