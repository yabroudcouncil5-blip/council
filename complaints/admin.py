from django import forms
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget
from core.admin_widgets import SelectionOnlyRelatedFieldsMixin

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
ASSIGNMENT_PRIORITIES = [
    ('low', 'منخفضة'), ('medium', 'متوسطة'), ('high', 'مرتفعة'), ('urgent', 'عاجلة'),
]


class CouncilAdmin(SelectionOnlyRelatedFieldsMixin, ModelAdmin):
    list_per_page = 25
    list_filter_submit = True
    save_on_top = True

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        kwargs['widget'] = UnfoldAdminSelectWidget
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


class AttachmentInline(SelectionOnlyRelatedFieldsMixin, TabularInline):
    model = ComplaintAttachment
    extra = 0
    can_delete = False
    fields = ('preview', 'file', 'original_name', 'source', 'visibility', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('preview', 'original_name', 'uploaded_by', 'uploaded_at')
    verbose_name = 'مرفق ودليل'
    verbose_name_plural = 'المرفقات والأدلة'

    @admin.display(description='معاينة')
    def preview(self, obj):
        if not obj or not obj.file:
            return '—'
        url = obj.file.url
        name = (obj.original_name or '').lower()
        if name.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            return format_html(
                '<a href="{}" target="_blank" rel="noopener" class="dashboard-attachment-preview">'
                '<img src="{}" alt="{}" loading="lazy" /></a>',
                url, url, obj.original_name,
            )
        if name.endswith('.pdf'):
            return format_html(
                '<iframe src="{}" title="{}" class="dashboard-attachment-pdf"></iframe>',
                url, obj.original_name,
            )
        return format_html('<a href="{}" target="_blank" rel="noopener">فتح المرفق</a>', url)

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_add_permission(request, obj)

class AssignmentInlineForm(forms.ModelForm):
    status = forms.ChoiceField(label='الحالة', choices=ASSIGNMENT_STATES, widget=UnfoldAdminSelectWidget)
    priority = forms.ChoiceField(label='الأولوية', choices=ASSIGNMENT_PRIORITIES, widget=UnfoldAdminSelectWidget)

    class Meta:
        model = ComplaintAssignment
        fields = ('department', 'status', 'priority', 'due_at')
        widgets = {'due_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')}


class AssignmentInline(SelectionOnlyRelatedFieldsMixin, TabularInline):
    model = ComplaintAssignment
    form = AssignmentInlineForm
    extra = 0
    can_delete = False
    fields = ('department', 'status', 'priority', 'due_at', 'assigned_at')
    readonly_fields = ('assigned_at',)
    verbose_name = 'إحالة إلى قسم'
    verbose_name_plural = 'الإحالات إلى الأقسام'

class ReviewInlineForm(forms.ModelForm):
    assignment = forms.ModelChoiceField(label='الإحالة المرتبطة', queryset=ComplaintAssignment.objects.none(), required=False, widget=UnfoldAdminSelectWidget)
    decision = forms.ChoiceField(
        label='قرار المراجعة',
        choices=[('', 'اختر قرار المراجعة'), *ComplaintReview.DECISIONS],
        widget=UnfoldAdminSelectWidget,
    )

    class Meta:
        model = ComplaintReview
        fields = ('assignment', 'decision', 'reason')
        widgets = {
            'decision': UnfoldAdminSelectWidget,
            'reason': UnfoldAdminTextareaWidget(attrs={'rows': 3, 'class': 'dashboard-review-notes'}),
        }


class ReviewInline(SelectionOnlyRelatedFieldsMixin, TabularInline):
    model = ComplaintReview
    form = ReviewInlineForm
    extra = 0
    can_delete = False
    fields = ('assignment', 'decision', 'reason', 'reviewer', 'created_at')
    readonly_fields = ('reviewer', 'created_at')
    verbose_name = 'مراجعة'
    verbose_name_plural = 'سجل المراجعات'

    def get_formset(self, request, obj=None, **kwargs):
        BaseFormSet = super().get_formset(request, obj, **kwargs)
        assignments = ComplaintAssignment.objects.filter(complaint=obj).order_by('-assigned_at') if obj else ComplaintAssignment.objects.none()

        class CurrentReviewerFormSet(BaseFormSet):
            def add_fields(self, form, index):
                super().add_fields(form, index)
                form.fields['assignment'].queryset = assignments

            def save_new(self, form, commit=True):
                form.instance.reviewer = request.user
                instance = super().save_new(form, commit=commit)
                if commit and instance:
                    status_map = {'approved': 'completed', 'closed': 'completed', 'returned': 'assigned', 'additional_assignment': 'transferred'}
                    next_status = status_map.get(instance.decision)
                    if instance.assignment and instance.decision == 'approved':
                        instance.assignment.status = 'approved'
                        instance.assignment.save(update_fields=('status',))
                    elif instance.assignment and instance.decision == 'returned':
                        instance.assignment.status = 'returned'
                        instance.assignment.save(update_fields=('status',))
                    if next_status:
                        complaint = instance.complaint
                        complaint.status = next_status
                        complaint.save(update_fields=('status', 'updated_at'))
                        ComplaintStatusHistory.objects.create(
                            complaint=complaint,
                            status=next_status,
                            actor=request.user,
                            public_message={
                                'completed': 'تم اعتماد المعالجة وإغلاق الشكوى',
                                'assigned': 'أعيدت الشكوى للقسم لاستكمال المعالجة',
                                'transferred': 'أحيلت الشكوى إلى قسم آخر لاستكمال المعالجة',
                            }[next_status],
                        )
                    if request.user.is_superuser and instance.decision == 'approved' and complaint.status == 'completed':
                        from django.utils import timezone
                        ComplaintPublication.objects.update_or_create(
                            complaint=complaint,
                            defaults={
                                'summary': instance.reason or 'تمت معالجة الشكوى واعتمادها.',
                                'visibility': 'tracked',
                                'approved': True,
                                'approved_by': request.user,
                                'published_at': timezone.now(),
                            },
                        )
                        ComplaintStatusHistory.objects.create(
                            complaint=complaint,
                            status='completed',
                            actor=request.user,
                            public_message='تم اعتماد الشكوى ونشر النتيجة للمواطن',
                        )
                return instance

        return CurrentReviewerFormSet


class PublicationInline(SelectionOnlyRelatedFieldsMixin, TabularInline):
    model = ComplaintPublication
    extra = 0
    max_num = 1
    can_delete = False
    fields = ('summary', 'visibility', 'approved', 'approved_by', 'published_at')
    readonly_fields = ('approved_by', 'published_at')
    verbose_name = 'تأكيد النشر للمواطن'
    verbose_name_plural = 'تأكيد النشر للمواطن'

    def has_add_permission(self, request, obj=None):
        return bool(request.user.is_superuser and obj and obj.status in {'completed', 'closed'} and super().has_add_permission(request, obj))

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        from django.utils import timezone
        for instance in instances:
            instance.approved = True
            instance.approved_by = request.user
            instance.published_at = timezone.now()
            instance.save()
            ComplaintStatusHistory.objects.create(
                complaint=instance.complaint,
                status=instance.complaint.status,
                actor=request.user,
                public_message='تم نشر نتيجة المعالجة للمواطن',
            )
        formset.save_m2m()


@admin.register(Complaint)
class ComplaintAdmin(CouncilAdmin):
    list_display = ('reference', 'title', 'category', 'status', 'submitted_at')
    list_filter = ('status', 'category', 'submitted_at')
    search_fields = ('reference', 'title', 'description', 'name', 'phone')
    ordering = ('-submitted_at',)
    list_select_related = ('category',)
    readonly_fields = ('reference', 'status', 'submitted_at', 'updated_at', 'staff_actions_review')
    fieldsets = (
        ('بيانات الشكوى', {'fields': ('reference', 'title', 'description', ('category', 'status'), 'location')}),
        ('بيانات التواصل مع المواطن', {'fields': ('name', ('phone', 'email')), 'description': 'بيانات داخلية؛ لا تُنشر على الموقع العام.'}),
        ('مراجعة إجراءات الفريق والأدلة', {'fields': ('staff_actions_review',), 'description': 'راجع الملاحظات والأدلة قبل اعتماد الشكوى أو إعادتها للقسم.'}),
        ('التواريخ', {'fields': ('submitted_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    inlines = (AssignmentInline, ReviewInline, AttachmentInline, HistoryInline)

    def has_add_permission(self, request):
        # Public submission creates and returns the complaint reference.
        return False

    @admin.display(description='إجراءات الفريق والأدلة')
    def staff_actions_review(self, obj):
        if not obj:
            return 'ستظهر إجراءات الفريق بعد إرسال المعالجة.'
        actions = AssignmentAction.objects.filter(assignment__complaint=obj).select_related('actor', 'assignment__department').prefetch_related('assignment__complaint__attachments').order_by('-created_at')
        if not actions.exists():
            return 'لم تُسجل إجراءات من الفريق بعد.'
        rows = []
        for action in actions:
            evidence = obj.attachments.filter(uploaded_by=action.actor, source='staff').order_by('-uploaded_at')
            evidence_links = [format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', item.file.url, item.original_name) for item in evidence if item.file]
            rows.append(format_html(
                '<article class="dashboard-action-review"><strong>{}</strong><span>{} · {}</span><p>{}</p>{}<p>{}</p></article>',
                action.assignment.department.name,
                action.actor.get_full_name() or action.actor.username,
                action.created_at.strftime('%Y/%m/%d %H:%M'),
                action.internal_action or 'لا توجد ملاحظات داخلية.',
                format_html('<p>الأدلة: {}</p>', format_html(' · '.join(str(link) for link in evidence_links))) if evidence_links else '',
                action.public_message or 'لا توجد رسالة عامة.',
            ))
        return format_html(''.join(str(row) for row in rows))


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = ComplaintAssignment
        fields = '__all__'
        widgets = {'due_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'), 'officer': forms.HiddenInput()}

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
    list_select_related = ('complaint', 'department', 'officer')
    readonly_fields = ('assigned_at',)
    ordering = ('-assigned_at',)
    fieldsets = (
        ('توجيه الشكوى', {'fields': ('complaint', 'department', 'officer'), 'description': 'اختر القسم فقط؛ يتولى فريق القسم توزيع المهمة داخلياً.'}),
        ('خطة المتابعة', {'fields': (('priority', 'status'), 'due_at', 'assigned_at')}),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'due_at':
            return forms.DateTimeField(label=LABELS['due_at'], required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'))
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        choices = {'status': ASSIGNMENT_STATES, 'priority': ASSIGNMENT_PRIORITIES}
        if db_field.name in choices:
            field = forms.ChoiceField(label=LABELS[db_field.name], choices=choices[db_field.name], widget=UnfoldAdminSelectWidget)
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
