from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    Complaint, ComplaintAssignment, AssignmentAction, ComplaintAttachment,
    RecoveryRequest, ComplaintReview, ComplaintPublication, InternalNotification,
    ComplaintStatusHistory,
)


LABELS = {
    'reference': 'الرقم المرجعي', 'title': 'موضوع الشكوى', 'description': 'تفاصيل الشكوى',
    'name': 'اسم المواطن', 'phone': 'رقم الهاتف', 'email': 'البريد الإلكتروني',
    'category': 'التصنيف', 'location': 'الموقع', 'status': 'الحالة',
    'submitted_at': 'تاريخ الاستلام', 'updated_at': 'آخر تحديث', 'complaint': 'الشكوى',
    'department': 'القسم المختص', 'officer': 'الموظف المسؤول', 'priority': 'الأولوية',
    'due_at': 'الموعد المحدد', 'assigned_at': 'تاريخ الإحالة', 'assignment': 'الإحالة',
    'actor': 'الموظف', 'internal_action': 'الإجراء الداخلي', 'public_message': 'الرسالة للمواطن',
    'created_at': 'تاريخ الإنشاء', 'reviewer': 'المراجع', 'decision': 'قرار المراجعة',
    'reason': 'الملاحظات والأسباب', 'summary': 'ملخص المعالجة', 'visibility': 'نطاق الظهور',
    'approved': 'معتمد للنشر', 'published_at': 'تاريخ النشر', 'approved_by': 'اعتمد بواسطة',
    'complaint_reference': 'الرقم المرجعي للشكوى', 'explanation': 'تفاصيل طلب الاستعادة',
    'contact': 'وسيلة التواصل', 'file': 'الملف', 'original_name': 'اسم الملف الأصلي',
    'uploaded_at': 'تاريخ الرفع', 'user': 'الموظف المستلم', 'message': 'نص التنبيه', 'read': 'مقروء',
}
ASSIGNMENT_STATES = [
    ('assigned', 'مسندة'), ('in_progress', 'قيد التنفيذ'), ('submitted', 'بانتظار الاعتماد'),
    ('approved', 'معتمدة'), ('returned', 'معادة للاستكمال'), ('cancelled', 'ملغاة'),
]


class CouncilAdmin(ModelAdmin):
    list_per_page = 25
    list_filter_submit = True
    save_on_top = True

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        kwargs['widget'] = forms.RadioSelect(attrs={'class': 'officer-choices'})
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in LABELS:
            kwargs['label'] = LABELS[db_field.name]
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class HistoryInline(TabularInline):
    model = ComplaintStatusHistory
    fields = ('status', 'public_message', 'actor', 'created_at')
    readonly_fields = fields
    extra = 0
    can_delete = False
    verbose_name = 'تحديث الحالة'
    verbose_name_plural = 'سجل تحديثات الشكوى'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Complaint)
class ComplaintAdmin(CouncilAdmin):
    radio_fields = {'category': admin.VERTICAL}
    list_display = ('reference', 'title', 'category', 'status', 'submitted_at')
    list_filter = ('status', 'category', 'submitted_at')
    search_fields = ('reference', 'title', 'description', 'name', 'phone')
    ordering = ('-submitted_at',)
    list_select_related = ('category',)
    readonly_fields = ('reference', 'submitted_at', 'updated_at')
    fieldsets = (
        ('بيانات الشكوى', {'fields': ('reference', 'title', 'description', ('category', 'status'), 'location')}),
        ('بيانات التواصل مع المواطن', {'fields': ('name', ('phone', 'email')), 'description': 'بيانات داخلية؛ لا تُنشر على الموقع العام.'}),
        ('التواريخ', {'fields': ('submitted_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    inlines = (HistoryInline,)

    def has_add_permission(self, request):
        # Public submission creates and returns the complaint reference.
        return False


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = ComplaintAssignment
        fields = '__all__'
        widgets = {'due_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')}

    def clean(self):
        data = super().clean()
        officer, department = data.get('officer'), data.get('department')
        if officer and (not officer.is_active or not officer.is_staff):
            self.add_error('officer', 'اختر موظفاً نشطاً لديه صلاحية الدخول إلى الإدارة.')
        if officer and department and not department.members.filter(pk=officer.pk).exists():
            self.add_error('officer', 'الموظف غير مرتبط بهذا القسم. حدّث أعضاء القسم أولاً.')
        return data


@admin.register(ComplaintAssignment)
class AssignmentAdmin(CouncilAdmin):
    form = AssignmentForm
    list_display = ('complaint', 'department', 'officer', 'status', 'priority', 'due_at')
    list_filter = ('status', 'priority', 'department')
    search_fields = ('complaint__reference', 'complaint__title', 'department__name', 'officer__username')
    autocomplete_fields = ('complaint',)
    radio_fields = {'department': admin.VERTICAL, 'officer': admin.VERTICAL}
    list_select_related = ('complaint', 'department', 'officer')
    readonly_fields = ('assigned_at',)
    ordering = ('-assigned_at',)
    fieldsets = (
        ('توجيه الشكوى', {'fields': ('complaint', 'department', 'officer'), 'description': 'اختر الشكوى ثم القسم والموظف المسؤول عن المتابعة.'}),
        ('خطة المتابعة', {'fields': (('priority', 'status'), 'due_at', 'assigned_at')}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'due_at':
            return forms.DateTimeField(label=LABELS['due_at'], required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'))
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        choices = {'status': ASSIGNMENT_STATES, 'priority': [('low', 'منخفضة'), ('medium', 'متوسطة'), ('high', 'مرتفعة'), ('urgent', 'عاجلة')]}
        if db_field.name in choices:
            field = forms.ChoiceField(label=LABELS[db_field.name], choices=choices[db_field.name], widget=forms.RadioSelect(attrs={'class': 'officer-choices'}))
        return field

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'officer':
            from django.contrib.auth import get_user_model
            kwargs['queryset'] = get_user_model().objects.filter(is_active=True, is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ComplaintReview
        fields = '__all__'

    def clean(self):
        data = super().clean()
        assignment, complaint = data.get('assignment'), data.get('complaint')
        if assignment and complaint and assignment.complaint_id != complaint.pk:
            self.add_error('assignment', 'الإحالة المختارة لا تتبع هذه الشكوى.')
        return data


@admin.register(ComplaintReview)
class ReviewAdmin(CouncilAdmin):
    form = ReviewForm
    list_display = ('complaint', 'assignment', 'decision', 'reviewer', 'created_at')
    list_filter = ('decision', 'created_at')
    search_fields = ('complaint__reference', 'complaint__title', 'reason')
    autocomplete_fields = ('complaint', 'assignment', 'reviewer')
    list_select_related = ('complaint', 'assignment', 'reviewer')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    fieldsets = (
        ('بيانات المراجعة', {'fields': ('complaint', 'assignment', 'reviewer')}),
        ('القرار والملاحظات', {'fields': ('decision', 'reason', 'created_at')}),
    )

    def get_changeform_initial_data(self, request):
        return {**super().get_changeform_initial_data(request), 'reviewer': request.user.pk}


@admin.register(AssignmentAction)
class ActionAdmin(CouncilAdmin):
    list_display = ('assignment', 'actor', 'created_at')
    search_fields = ('assignment__complaint__reference', 'internal_action')
    autocomplete_fields = ('assignment', 'actor')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('بيانات التنفيذ', {'fields': ('assignment', 'actor')}),
        ('تفاصيل الإجراء', {'fields': ('internal_action', 'public_message', 'created_at')}),
    )


@admin.register(ComplaintAttachment)
class AttachmentAdmin(CouncilAdmin):
    list_display = ('original_name', 'complaint', 'visibility', 'uploaded_at')
    search_fields = ('original_name', 'complaint__reference')
    list_filter = ('visibility',)
    autocomplete_fields = ('complaint',)
    readonly_fields = ('uploaded_at',)


@admin.register(RecoveryRequest)
class RecoveryAdmin(CouncilAdmin):
    list_display = ('complaint_reference', 'contact', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('complaint_reference', 'contact', 'explanation')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(ComplaintPublication)
class PublicationAdmin(CouncilAdmin):
    list_display = ('complaint', 'visibility', 'approved', 'published_at')
    list_filter = ('visibility', 'approved')
    search_fields = ('complaint__reference', 'summary')
    autocomplete_fields = ('complaint', 'approved_by')
    fieldsets = (
        ('ملخص المعالجة', {'fields': ('complaint', 'summary')}),
        ('إعدادات النشر', {'fields': ('visibility', 'approved', 'approved_by', 'published_at'), 'description': 'تظهر النتيجة للعامة فقط إذا كانت الشكوى معالجة والنشر عاماً ومعتمداً.'}),
    )


@admin.register(InternalNotification)
class NotificationAdmin(CouncilAdmin):
    list_display = ('message', 'user', 'read', 'created_at')
    list_filter = ('read',)
    search_fields = ('message', 'user__username', 'complaint__reference')
    autocomplete_fields = ('user', 'complaint')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
