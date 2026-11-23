from django import forms
from django.contrib import admin
from django.db.models import Case, IntegerField, OuterRef, Subquery, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget
from core.admin_widgets import SelectionOnlyRelatedFieldsMixin
from .deadlines import deadline_badge
from .workflow import assignments_for, can_review, complaints_for

from .models import (
    Complaint, ComplaintAssignment, AssignmentAction, ComplaintAttachment,
    RecoveryRequest, ComplaintReview, ComplaintPublication, InternalNotification,
    ComplaintStatusHistory, ASSIGNMENT_PRIORITIES, ASSIGNMENT_STATES,
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
    template = 'complaints/admin/history_inline.html'
    fields = ('stage', 'public_message', 'actor', 'created_at')
    readonly_fields = fields
    extra = 0
    can_delete = False
    verbose_name = 'تحديث الحالة'
    verbose_name_plural = 'سجل تحديثات الشكوى'

    def has_add_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        visible = complaints_for(request.user)
        return visible.filter(pk=obj.pk).exists() if obj else (can_review(request.user) or visible.exists())

    @admin.display(description='المرحلة')
    def stage(self, obj):
        return dict(Complaint.STATUS).get(obj.status, 'تحديث الحالة')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('actor').order_by('created_at', 'pk')


class CompactComplaintInline(SelectionOnlyRelatedFieldsMixin, StackedInline):
    template = 'complaints/admin/compact_inline.html'
    extra = 0
    can_delete = False


class AttachmentInlineForm(forms.ModelForm):
    visibility = forms.ChoiceField(
        label='نطاق الظهور',
        choices=(('internal', 'داخلي — للمراجعة فقط'), ('public', 'للمواطن بعد اعتماد النشر')),
        widget=UnfoldAdminSelectWidget,
    )

    class Meta:
        model = ComplaintAttachment
        fields = '__all__'


class AttachmentInline(CompactComplaintInline):
    model = ComplaintAttachment
    form = AttachmentInlineForm
    fields = ('preview', 'file', 'original_name', 'source', 'visibility', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('preview', 'original_name', 'uploaded_by', 'uploaded_at')
    verbose_name = 'مرفق ودليل'
    verbose_name_plural = 'المرفقات والأدلة'

    @admin.display(description='معاينة')
    def preview(self, obj):
        if not obj or not obj.file:
            return '—'
        url = reverse('complaint-evidence', args=[obj.pk])
        name = (obj.original_name or obj.file.name).lower()
        if name.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            return format_html(
                '<a href="{}" target="_blank" rel="noopener" class="dashboard-attachment-preview">'
                '<img src="{}" alt="{}" loading="lazy" /></a>',
                url, url + '?preview=1', obj.original_name,
            )
        if name.endswith('.pdf'):
            return format_html(
                '<iframe src="{}" title="{}" class="dashboard-attachment-pdf"></iframe>',
                url, obj.original_name,
            )
        return format_html('<a href="{}" target="_blank" rel="noopener">فتح المرفق</a>', url)

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_add_permission(request, obj)



class WorkflowRecordInline(CompactComplaintInline):
    """Assignment/review records are an audit trail, not another status editor."""
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        visible = complaints_for(request.user)
        return visible.filter(pk=obj.pk).exists() if obj else (can_review(request.user) or visible.exists())


class AssignmentRecordInline(WorkflowRecordInline):
    model = ComplaintAssignment
    fields = readonly_fields = ('department', 'stage', 'priority_label', 'due_at', 'assigned_at')
    verbose_name = 'إحالة'
    verbose_name_plural = 'سجل إحالات الأقسام'

    @admin.display(description='المرحلة')
    def stage(self, obj):
        return dict(ASSIGNMENT_STATES).get(obj.status, obj.status)

    @admin.display(description='الأولوية')
    def priority_label(self, obj):
        return obj.priority_label


class ReviewRecordInline(WorkflowRecordInline):
    model = ComplaintReview
    fields = readonly_fields = ('assignment', 'decision', 'reason', 'reviewer', 'created_at')
    verbose_name = 'قرار مراجعة'
    verbose_name_plural = 'سجل قرارات المراجعة — ملاحظات داخلية'


class EvidenceRecordInline(WorkflowRecordInline):
    model = ComplaintAttachment
    preview = AttachmentInline.preview
    fields = readonly_fields = ('preview', 'original_name', 'source', 'audience', 'uploaded_by', 'uploaded_at')
    verbose_name_plural = 'أدلة المواطن وفريق البلدية'

    @admin.display(description='نطاق الظهور')
    def audience(self, obj):
        publication = getattr(obj.complaint, 'publication', None)
        visible = obj.source == 'staff' and obj.visibility == 'public' and publication and publication.approved and obj.complaint.status in {'completed', 'closed'}
        return 'منشور مع النتيجة المعتمدة' if visible else 'داخلي — للمراجعة فقط'


class ComplaintAttentionFilter(admin.SimpleListFilter):
    title = 'المتابعة'
    parameter_name = 'attention'

    def lookups(self, request, model_admin):
        return (('urgent', 'عاجلة جداً'), ('overdue', 'متأخرة'))

    def queryset(self, request, queryset):
        if self.value() == 'urgent':
            return queryset.filter(visible_priority_rank=len(ASSIGNMENT_PRIORITIES))
        if self.value() == 'overdue':
            return queryset.filter(visible_deadline__lt=timezone.now())
        return queryset


@admin.register(Complaint)
class ComplaintAdmin(CouncilAdmin):
    list_display = ('reference', 'title', 'category', 'status', 'open_priority', 'open_deadline', 'submitted_at')
    list_filter = (ComplaintAttentionFilter, 'status', 'category', 'submitted_at')
    change_list_template = 'complaints/admin/complaint_list.html'
    search_fields = ('reference', 'title', 'description', 'name', 'phone')
    list_select_related = ('category',)
    readonly_fields = ('reference', 'status', 'submitted_at', 'updated_at', 'staff_actions_review')
    fieldsets = (
        ('بيانات الشكوى', {'fields': ('title', 'description', ('category', 'location')), 'classes': ('case-main-fields',)}),
        ('عمل الفريق والملاحظات الداخلية', {'fields': ('staff_actions_review',), 'classes': ('case-team-fields',)}),
        ('بيانات التواصل مع المواطن', {
            'fields': (('name', 'phone', 'email'),),
            'description': 'بيانات داخلية.',
            'classes': ('case-private-fields',),
        }),
        ('بيانات التسجيل', {
            'fields': (('reference', 'status'), ('submitted_at', 'updated_at')),
            'classes': ('case-private-fields',),
        }),
    )
    inlines = (AssignmentRecordInline, EvidenceRecordInline, ReviewRecordInline, HistoryInline)
    change_form_template = 'complaints/admin/complaint_detail.html'

    def get_queryset(self, request):
        open_assignments = assignments_for(request.user).filter(
            complaint_id=OuterRef('pk'),
        ).exclude(status__in=['approved', 'cancelled'])
        ranked = open_assignments.annotate(priority_rank=Case(
            *(When(priority=key, then=Value(rank))
              for rank, (key, _) in enumerate(ASSIGNMENT_PRIORITIES, start=1)),
            default=Value(0),
            output_field=IntegerField(),
        ))
        deadlines = open_assignments.filter(due_at__isnull=False).order_by('due_at')
        return super().get_queryset(request).filter(
            pk__in=complaints_for(request.user).values('pk'),
        ).annotate(
            visible_priority_rank=Coalesce(
                Subquery(ranked.order_by('-priority_rank').values('priority_rank')[:1]), Value(0),
            ),
            visible_deadline=Subquery(deadlines.values('due_at')[:1]),
        ).alias(
            urgent_first=Case(When(visible_priority_rank=len(ASSIGNMENT_PRIORITIES), then=Value(1)), default=Value(0)),
            overdue_first=Case(When(visible_deadline__lt=timezone.now(), then=Value(1)), default=Value(0)),
        ).order_by('-urgent_first', '-overdue_first', '-submitted_at')

    @admin.display(description='الأولوية', ordering='visible_priority_rank', empty_value='غير محددة')
    def open_priority(self, obj):
        if obj.visible_priority_rank:
            key, label = ASSIGNMENT_PRIORITIES[obj.visible_priority_rank - 1]
            return format_html('<span class="followup-badge followup-badge--{}">{}</span>', key, label)

    @admin.display(description='المهلة بالأيام', ordering='visible_deadline', empty_value='غير محددة')
    def open_deadline(self, obj):
        if obj.visible_deadline:
            return deadline_badge(obj.visible_deadline, timezone.now())

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_staff and (can_review(request.user) or
                    (complaints_for(request.user).filter(pk=obj.pk).exists() if obj else complaints_for(request.user).exists())))

    def has_change_permission(self, request, obj=None):
        return can_review(request.user)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def get_readonly_fields(self, request, obj=None):
        if not can_review(request.user):
            return (*self.readonly_fields, 'title', 'description', 'category', 'location', 'name', 'phone', 'email')
        return self.readonly_fields

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        from .workflow_forms import ComplaintWorkflowForm
        from .workflow import available_actions
        obj = self.get_object(request, object_id) if object_id else None
        extra_context = dict(extra_context or {})
        if obj and self.has_view_permission(request, obj):
            extra_context.update({
                'workflow_complaint': obj,
                'workflow_priority': self.open_priority(obj),
                'workflow_deadline': self.open_deadline(obj),
                'workflow_form': ComplaintWorkflowForm(complaint=obj, user=request.user),
                'workflow_actions': available_actions(request.user, obj),
                'workflow_reviewer': can_review(request.user),
                'workflow_latest_review': obj.reviews.select_related('reviewer', 'assignment__department').order_by('-created_at', '-pk').first(),
                'workflow_evidence': obj.attachments.filter(source='staff'),
            })
        return super().changeform_view(request, object_id, form_url, extra_context)

    def has_add_permission(self, request):
        # Public submission creates and returns the complaint reference.
        return False

    @admin.display(description='الملاحظات والإجراءات والأدلة')
    def staff_actions_review(self, obj):
        if not obj:
            return 'ستظهر الملاحظات والإجراءات المسجلة هنا.'
        actions = AssignmentAction.objects.filter(assignment__complaint=obj).select_related('actor', 'assignment__department').prefetch_related('assignment__complaint__attachments').order_by('-created_at')
        if not actions.exists():
            return 'لم تُسجل ملاحظات أو إجراءات من الفريق بعد.'
        rows = []
        for action in actions:
            evidence = obj.attachments.filter(uploaded_by=action.actor, source='staff').order_by('-uploaded_at') if action.kind == 'submission' else []
            rows.append({
                'action': action,
                'evidence': [
                    {'attachment': item, 'preview': AttachmentInline.preview(self, item)}
                    for item in evidence if item.file
                ],
            })
        return render_to_string('complaints/admin/staff_actions.html', {'rows': rows})


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
    # Assignments are managed from the complaint detail page. Keep the
    # model registered for existing links and data integrity, but remove the
    # confusing standalone page from the admin navigation.
    def get_model_perms(self, request):
        return {}

    def has_module_permission(self, request):
        return False

    def get_urls(self):
        """Keep legacy assignment URLs from opening a confusing standalone page."""
        def go_to_complaints(request, object_id=None):
            target = 'admin:complaints_complaint_changelist'
            if object_id:
                assignment = self.get_object(request, object_id)
                if assignment and self.has_view_or_change_permission(request, assignment):
                    return redirect('admin:complaints_complaint_change', assignment.complaint_id)
            return redirect(target)

        view = self.admin_site.admin_view(go_to_complaints)
        prefix = f'{self.opts.app_label}_{self.opts.model_name}'
        return [
            path('', view, name=f'{prefix}_changelist'),
            path('add/', view, name=f'{prefix}_add'),
            path('<path:object_id>/change/', view, name=f'{prefix}_change'),
            path('<path:object_id>/delete/', view, name=f'{prefix}_delete'),
            path('<path:object_id>/history/', view, name=f'{prefix}_history'),
            path('<path:object_id>/', view),
        ]

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


class WorkflowAuditAdmin(CouncilAdmin):
    """Workflow changes are made once, inside the complaint's action panel."""
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_model_perms(self, request):
        return {}

    def has_module_permission(self, request):
        return False

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        field = 'assignment__complaint__in' if self.model is AssignmentAction else 'complaint__in'
        return queryset.filter(**{field: complaints_for(request.user)})


@admin.register(ComplaintReview)
class ReviewAdmin(WorkflowAuditAdmin):
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
class ActionAdmin(WorkflowAuditAdmin):
    list_display = ('assignment', 'kind', 'actor', 'created_at')
    search_fields = ('assignment__complaint__reference', 'internal_action')
    autocomplete_fields = ('assignment', 'actor')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('بيانات التنفيذ', {'fields': ('assignment', 'actor')}),
        ('تفاصيل الإجراء', {'fields': ('kind', 'internal_action', 'public_message', 'created_at')}),
    )


@admin.register(ComplaintAttachment)
class AttachmentAdmin(WorkflowAuditAdmin):
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

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset if can_review(request.user) else queryset.filter(
            complaint_reference__in=complaints_for(request.user).values('reference'),
        )

    def has_add_permission(self, request):
        return can_review(request.user)

    def has_change_permission(self, request, obj=None):
        return can_review(request.user)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser


@admin.register(ComplaintPublication)
class PublicationAdmin(WorkflowAuditAdmin):
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

    def get_queryset(self, request):
        from .workflow import notifications_for
        queryset = super().get_queryset(request)
        return queryset if request.user.is_superuser else queryset.filter(
            pk__in=notifications_for(request.user).values('pk'),
        )

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ('message', 'user', 'complaint', 'created_at')
        return self.readonly_fields

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser
