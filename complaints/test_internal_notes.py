from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Department
from .models import AssignmentAction, Complaint, ComplaintAssignment
from .tracking import tracking_result
from .workflow import WorkflowError, available_actions, transition
from .workflow_forms import ComplaintWorkflowForm


class StaffInternalNotesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('notes-admin', password='test-password')
        cls.reviewer = User.objects.create_user('notes-reviewer', is_staff=True)
        cls.reviewer.groups.add(Group.objects.create(name='Complaint Reviewer'))
        cls.staff = User.objects.create_user('notes-staff', first_name='أحمد', last_name='خالد', is_staff=True)
        cls.staff.groups.add(Group.objects.create(name='Department Officer'))
        cls.department = Department.objects.create(name='الإنارة')
        cls.department.members.add(cls.staff)
        cls.foreign = Department.objects.create(name='النظافة')

    def setUp(self):
        self.complaint = Complaint.objects.create(reference='INTERNAL-NOTES', title='مصباح معطل', description='تفاصيل')
        _, self.assignment = transition(self.complaint.pk, self.admin, 'assign', department_id=self.department.pk)
        self.complaint.refresh_from_db()

    def test_internal_note_is_timestamped_without_changing_assignment_stage_or_public_history(self):
        before = tracking_result({'reference': self.complaint.reference})
        old_version = self.complaint.updated_at
        history_count = self.complaint.status_history.count()
        transition(self.complaint.pk, self.staff, 'note', internal_note=' PRIVATE site visit note ', public_message='DO NOT PUBLISH')
        note = self.assignment.actions.get()
        self.assertEqual((note.kind, note.actor, note.internal_action), ('note', self.staff, 'PRIVATE site visit note'))
        self.assertEqual(note.public_message, '')
        self.assertIsNotNone(note.created_at)
        self.assignment.refresh_from_db()
        self.complaint.refresh_from_db()
        self.assertEqual(self.assignment.status, 'assigned')
        self.assertEqual(self.complaint.status, 'assigned')
        self.assertGreater(self.complaint.updated_at, old_version)
        self.assertEqual(self.complaint.status_history.count(), history_count)
        self.assertEqual(tracking_result({'reference': self.complaint.reference}), before)
        self.assertEqual(available_actions(self.staff, self.complaint), ['start', 'note', 'submit'])

    def test_staff_form_opens_on_internal_notes_and_saves_without_public_fields(self):
        form = ComplaintWorkflowForm(complaint=self.complaint, user=self.staff)
        self.assertEqual(form['action'].value(), 'note')
        self.assertIn('الملاحظات الداخلية', form.fields['internal_note'].label)
        self.assertIn('اختياري', form.fields['public_message'].label)
        self.client.force_login(self.staff)
        response = self.client.post(reverse('complaint-transition', args=[self.complaint.pk]), {
            'action': 'note', 'internal_note': 'PRIVATE inspection report',
            'version': self.complaint.updated_at.isoformat(),
        }, follow=True)
        self.assertContains(response, 'تم حفظ الملاحظة الداخلية دون تغيير مرحلة الشكوى أو التتبع العام.')
        self.assertContains(response, 'PRIVATE inspection report')
        self.assertContains(response, 'أحمد خالد')
        self.assertContains(response, 'ملاحظة داخلية')
        self.assertEqual(self.assignment.actions.get().kind, 'note')
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, 'assigned')

    def test_legacy_staff_action_endpoint_also_saves_notes_without_submitting_work(self):
        self.client.force_login(self.staff)
        response = self.client.post('/staff/action/', {
            'assignment_id': self.assignment.pk, 'action': 'note', 'internal_note': 'PRIVATE repair scheduled',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'assigned')
        self.assertEqual(self.assignment.actions.get().kind, 'note')

    def test_empty_notes_and_unexpected_uploads_are_rejected(self):
        with self.assertRaises(WorkflowError):
            transition(self.complaint.pk, self.staff, 'note', internal_note='  ')
        upload = SimpleUploadedFile('proof.pdf', b'%PDF-1.4 proof', content_type='application/pdf')
        with self.assertRaises(WorkflowError):
            transition(self.complaint.pk, self.staff, 'note', internal_note='PRIVATE note', uploads=[upload])
        self.assertFalse(self.assignment.actions.exists())
        self.assertFalse(self.complaint.attachments.exists())
        form = ComplaintWorkflowForm(data={
            'action': 'note', 'internal_note': '', 'version': self.complaint.updated_at.isoformat(),
        }, complaint=self.complaint, user=self.staff)
        self.assertFalse(form.is_valid())
        self.assertIn('internal_note', form.errors)

    def test_reviewer_sees_notes_and_submitted_work_but_residents_never_see_internal_notes(self):
        transition(self.complaint.pk, self.staff, 'note', internal_note='PRIVATE visit planned')
        transition(self.complaint.pk, self.staff, 'start')
        transition(self.complaint.pk, self.staff, 'note', internal_note='PRIVATE replacement required')
        transition(self.complaint.pk, self.staff, 'submit', internal_note='PRIVATE completed repair', public_message='اكتمل إصلاح المصباح')
        self.assertEqual(self.assignment.actions.filter(kind='note').count(), 2)
        self.assertEqual(self.assignment.actions.filter(kind='submission').count(), 1)
        self.client.force_login(self.reviewer)
        response = self.client.get(reverse('admin:complaints_complaint_change', args=[self.complaint.pk]))
        for text in ('PRIVATE visit planned', 'PRIVATE replacement required', 'PRIVATE completed repair', 'أحمد خالد', 'إجراء مرسل للمراجعة'):
            self.assertContains(response, text)
        transition(self.complaint.pk, self.reviewer, 'approved', public_message='تم الإصلاح والتحقق من العمل', confirm=True)
        self.client.logout()
        for path in ('/', '/complaints/track/', '/api/complaints/track/'):
            response = self.client.get(path, {'reference': self.complaint.reference})
            self.assertNotContains(response, 'PRIVATE')
            self.assertNotContains(response, 'أحمد خالد')
            self.assertContains(response, 'تم الإصلاح والتحقق من العمل')

    def test_progress_notes_cannot_count_as_submitted_work_for_approval(self):
        transition(self.complaint.pk, self.staff, 'note', internal_note='PRIVATE unfinished work')
        ComplaintAssignment.objects.filter(pk=self.assignment.pk).update(status='submitted')
        Complaint.objects.filter(pk=self.complaint.pk).update(status='final_review')
        with self.assertRaises(WorkflowError):
            transition(self.complaint.pk, self.reviewer, 'approved', public_message='غير مكتمل', confirm=True)
        self.assertFalse(self.complaint.reviews.exists())

    def test_saving_notes_does_not_prefill_the_public_result_or_synthesize_a_public_stage(self):
        transition(self.complaint.pk, self.staff, 'submit', internal_note='PRIVATE repair', public_message='ملخص المعالجة المقترح')
        # A separate progress entry must never become the proposed public result.
        AssignmentAction.objects.create(assignment=self.assignment, actor=self.staff, kind='note', internal_action='PRIVATE later note')
        self.complaint.refresh_from_db()
        form = ComplaintWorkflowForm(complaint=self.complaint, user=self.reviewer)
        self.assertEqual(form['public_message'].value(), 'ملخص المعالجة المقترح')
        result = tracking_result({'reference': self.complaint.reference})
        self.assertEqual([item['status_code'] for item in result['timeline']], ['submitted', 'assigned', 'final_review'])

    def test_notes_require_current_department_assignment_and_cannot_be_added_after_submission(self):
        other = Complaint.objects.create(reference='FOREIGN-NOTES', title='أخرى', description='تفاصيل')
        transition(other.pk, self.admin, 'assign', department_id=self.foreign.pk)
        with self.assertRaises(PermissionDenied):
            transition(other.pk, self.staff, 'note', internal_note='FORGED')
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(reverse('complaint-transition', args=[other.pk]), {
            'action': 'note', 'internal_note': 'FORGED', 'version': other.updated_at.isoformat(),
        }).status_code, 404)
        transition(self.complaint.pk, self.staff, 'submit', internal_note='تم العمل')
        with self.assertRaises(WorkflowError):
            transition(self.complaint.pk, self.staff, 'note', internal_note='Too late')

    def test_notes_are_append_only_and_follow_optimistic_locking(self):
        version = self.complaint.updated_at.isoformat()
        transition(self.complaint.pk, self.staff, 'note', internal_note='PRIVATE first note', version=version)
        with self.assertRaises(WorkflowError) as error:
            transition(self.complaint.pk, self.staff, 'note', internal_note='Stale note', version=version)
        self.assertEqual(error.exception.status, 409)
        note = self.assignment.actions.get()
        self.client.force_login(self.admin)
        for suffix, data in (('change/', {'internal_action': 'FORGED'}), ('delete/', {'post': 'yes'})):
            self.assertEqual(self.client.post(f'/admin/complaints/assignmentaction/{note.pk}/' + suffix, data).status_code, 403)
        note.refresh_from_db()
        self.assertEqual(note.internal_action, 'PRIVATE first note')
