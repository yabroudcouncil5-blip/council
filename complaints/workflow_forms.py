from django import forms
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextareaWidget

from core.models import Department
from .models import AssignmentAction, ComplaintAttachment
from .workflow import ACTION_LABELS, available_actions, can_review


class MultipleEvidenceInput(forms.ClearableFileInput):
    allow_multiple_selected = True
    template_name = 'complaints/admin/evidence_input.html'


class EvidenceUploadField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return []
        return [super(EvidenceUploadField, self).clean(item, initial) for item in (data if isinstance(data, (list, tuple)) else [data])]


class ComplaintWorkflowForm(forms.Form):
    action = forms.ChoiceField(label='الإجراء التالي', widget=UnfoldAdminSelectWidget)
    department = forms.ModelChoiceField(label='القسم المختص', queryset=Department.objects.filter(active=True),
                                        required=False, empty_label='اختر القسم', widget=UnfoldAdminSelectWidget)
    priority = forms.ChoiceField(label='الأولوية', required=False, initial='medium', widget=UnfoldAdminSelectWidget,
                                choices=[('medium', 'عادية'), ('high', 'مرتفعة'), ('urgent', 'عاجلة'), ('low', 'منخفضة')])
    due_at = forms.DateTimeField(label='الموعد المحدد', required=False,
                                widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    internal_note = forms.CharField(label='الملاحظات الداخلية وتفاصيل الإجراء', required=False,
                                    widget=UnfoldAdminTextareaWidget(attrs={
                                        'rows': 3, 'placeholder': 'اكتب ما تم عمله، وما يحتاج إلى متابعة، وأي ملاحظات للفريق والمراجع.',
                                    }))
    public_message = forms.CharField(label='النتيجة التي ستظهر للمواطن', required=False,
                                     widget=UnfoldAdminTextareaWidget(attrs={'rows': 3}),
                                     help_text='تُنشر عند الاعتماد فقط. لا تُدرج بيانات شخصية أو ملاحظات داخلية.')
    evidence_ids = forms.ModelMultipleChoiceField(label='أدلة البلدية التي ستُنشر مع النتيجة', required=False,
                                                  queryset=ComplaintAttachment.objects.none(), widget=forms.CheckboxSelectMultiple)
    evidence = EvidenceUploadField(label='إرفاق صور أو ملفات PDF', required=False,
                                   widget=MultipleEvidenceInput(attrs={
                                       'accept': '.jpg,.jpeg,.png,.webp,.pdf',
                                       'x-bind:disabled': "!['submit','approved','closed','publish'].includes(action)",
                                   }))
    confirm = forms.BooleanField(label='راجعت الإجراء والأدلة وأؤكد نشر النتيجة والأدلة المختارة للمواطن', required=False)
    version = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, complaint, user, **kwargs):
        super().__init__(*args, **kwargs)
        actions = available_actions(user, complaint)
        self.fields['action'].choices = [('', 'اختر الإجراء'), *[(action, ACTION_LABELS[action]) for action in actions]]
        self.fields['action'].widget.attrs['x-model'] = 'action'
        self.fields['version'].initial = complaint.updated_at.isoformat()
        self.fields['evidence_ids'].queryset = complaint.attachments.filter(source='staff').order_by('uploaded_at')
        self.fields['evidence_ids'].label_from_instance = lambda item: item.original_name or item.file.name
        if not can_review(user):
            if 'note' in actions:
                self.fields['action'].initial = 'note'
            self.fields['public_message'].label = 'ملخص مقترح للمراجع (اختياري)'
            self.fields['public_message'].help_text = 'مقترح للمراجع؛ لا يُنشر قبل الاعتماد.'
        publication = getattr(complaint, 'publication', None)
        if publication and complaint.status in {'completed', 'closed'}:
            self.fields['public_message'].initial = publication.summary
        elif can_review(user) and complaint.status == 'final_review':
            action = AssignmentAction.objects.filter(assignment__complaint=complaint, kind='submission').order_by('-created_at', '-pk').first()
            if action:
                self.fields['public_message'].initial = action.public_message
        if publication and publication.approved and complaint.status in {'completed', 'closed'}:
            self.fields['evidence_ids'].initial = list(complaint.attachments.filter(source='staff', visibility='public').values_list('pk', flat=True))

    def clean(self):
        data = super().clean()
        action = data.get('action')
        if action == 'note' and not data.get('internal_note', '').strip():
            self.add_error('internal_note', 'اكتب الملاحظة الداخلية قبل حفظها.')
        if action in {'assign', 'additional_assignment'} and not data.get('department'):
            self.add_error('department', 'اختر القسم المختص.')
        if action in {'submit', 'returned', 'additional_assignment'} and not data.get('internal_note', '').strip():
            self.add_error('internal_note', 'اكتب الإجراء المتخذ أو سبب الإعادة والتحويل.')
        if action in {'approved', 'closed', 'publish'}:
            if not data.get('public_message', '').strip():
                self.add_error('public_message', 'اكتب النتيجة التي ستظهر للمواطن.')
            if not data.get('confirm'):
                self.add_error('confirm', 'راجع الإجراء والأدلة ثم أكد الاعتماد والنشر.')
        return data
