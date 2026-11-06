import importlib
import tempfile
from datetime import timedelta
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Department
from .models import (AssignmentAction, Complaint, ComplaintAssignment, ComplaintAttachment,
                     ComplaintPublication, ComplaintReview, ComplaintStatusHistory)
from .tracking import tracking_result
from .workflow import WorkflowError, transition


class UnifiedComplaintWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('flow-admin', password='test-password')
        cls.reviewer = User.objects.create_user('flow-reviewer', is_staff=True)
        cls.reviewer.groups.add(Group.objects.create(name='Complaint Reviewer'))
        cls.staff = User.objects.create_user('flow-staff', is_staff=True)
        cls.other_staff = User.objects.create_user('other-department', is_staff=True)
        cls.department = Department.objects.create(name='الإنارة')
        cls.other = Department.objects.create(name='النظافة')
        cls.department.members.add(cls.staff)
        cls.other.members.add(cls.other_staff)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.temp.name)
        self.settings_override.enable()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.settings_override.disable)
        self.complaint = Complaint.objects.create(reference='YBC-FLOW-1', title='Private title',
            description='Private description', name='Private resident', phone='Private phone',
            email='private@example.com')

    def route(self):
        return transition(self.complaint.pk, self.admin, 'assign', department_id=self.department.pk)[1]

    def submit(self, *, upload=False):
        assignment = self.route()
        uploads = [SimpleUploadedFile('proof.png', b'council-proof', content_type='image/png')] if upload else []
        transition(self.complaint.pk, self.staff, 'submit', internal_note='PRIVATE staff note',
                   public_message='UNAPPROVED staff proposal', uploads=uploads)
        return assignment

    def approve(self, evidence_ids=(), user=None):
        return transition(self.complaint.pk, user or self.reviewer, 'approved',
                          internal_note='PRIVATE reviewer note', public_message='اكتمل إصلاح الإنارة بعد الفحص',
                          evidence_ids=evidence_ids, confirm=True)

    def assert_shared(self, code):
        self.complaint.refresh_from_db()
        result = tracking_result({'reference': self.complaint.reference})
        self.assertEqual(self.complaint.status, code)
        self.assertEqual(result['status_code'], code)
        self.assertEqual(result['status'], self.complaint.get_status_display())
        self.assertEqual(result['timeline'][-1]['status_code'], code)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/admin/'), self.complaint.get_status_display())
        self.assertContains(self.client.get('/admin/complaints/complaint/'), self.complaint.get_status_display())
        return result

    def test_complete_flow_has_identical_dashboard_tracker_stage_and_ordered_history(self):
        self.assert_shared('submitted')
        self.route()
        self.assert_shared('assigned')
        transition(self.complaint.pk, self.staff, 'start')
        self.assert_shared('in_progress')
        transition(self.complaint.pk, self.staff, 'submit', internal_note='PRIVATE repair details')
        self.assert_shared('final_review')
        self.approve()
        result = self.assert_shared('completed')
        self.assertEqual([event['status_code'] for event in result['timeline']],
                         ['submitted', 'assigned', 'in_progress', 'final_review', 'completed'])
        self.assertEqual(result['timeline'][-1]['public_message'], 'اكتمل إصلاح الإنارة بعد الفحص')
        self.assertTrue(ComplaintPublication.objects.get(complaint=self.complaint).approved)

    def test_reviewer_without_raw_model_permissions_sees_the_whole_case_audit_trail(self):
        self.submit(upload=True)
        self.client.force_login(self.reviewer)
        response = self.client.get(f'/admin/complaints/complaint/{self.complaint.pk}/change/')
        self.assertContains(response, 'PRIVATE staff note')
        self.assertContains(response, 'proof.png')
        self.assertNotContains(response, 'لا توجد تحديثات مسجلة بعد.')
        self.assertContains(response, 'تمت إحالة الشكوى إلى قسم الإنارة')
        self.assertContains(response, reverse('complaint-evidence', args=[self.complaint.attachments.get().pk]))

    def test_public_tracker_never_exposes_private_fields_or_unapproved_notes(self):
        self.submit()
        for path in ('/', '/complaints/track/', '/api/complaints/track/'):
            response = self.client.get(path, {'reference': self.complaint.reference})
            self.assertNotContains(response, 'PRIVATE')
            self.assertNotContains(response, 'Private')
            self.assertNotContains(response, 'UNAPPROVED')
        self.approve()
        response = self.client.get('/', {'reference': self.complaint.reference})
        self.assertNotContains(response, 'PRIVATE reviewer note')
        self.assertContains(response, 'اكتمل إصلاح الإنارة بعد الفحص')

    def test_selected_council_proof_is_inline_after_approval_not_before(self):
        self.submit(upload=True)
        proof = self.complaint.attachments.get()
        url = reverse('complaint-evidence', args=[proof.pk])
        self.assertEqual(proof.source, 'staff')
        self.assertEqual(proof.uploaded_by, self.staff)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertNotIn('evidence', tracking_result({'reference': self.complaint.reference}))
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.approve([proof.pk])
        self.assertEqual(tracking_result({'reference': self.complaint.reference})['evidence'], [url])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertIn('inline;', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertContains(self.client.get('/', {'reference': self.complaint.reference}), f'src="{url}?preview=1"')

    def test_resident_attachments_and_unselected_staff_proof_stay_private(self):
        self.submit(upload=True)
        resident = ComplaintAttachment.objects.create(complaint=self.complaint, source='resident',
            file=SimpleUploadedFile('resident.png', b'private', content_type='image/png'), original_name='resident.png', visibility='public')
        self.approve()
        self.assertNotIn('evidence', tracking_result({'reference': self.complaint.reference}))
        for proof in self.complaint.attachments.all():
            self.assertEqual(self.client.get(reverse('complaint-evidence', args=[proof.pk])).status_code, 404)
        with self.assertRaises(WorkflowError):
            transition(self.complaint.pk, self.admin, 'publish', public_message='تم الحل', evidence_ids=[resident.pk], confirm=True)

    def test_admin_can_upload_and_publish_proof_with_approval(self):
        self.submit()
        transition(self.complaint.pk, self.admin, 'approved', public_message='اكتمل العمل', confirm=True,
                   uploads=[SimpleUploadedFile('admin.pdf', b'%PDF-1.4 proof', content_type='application/pdf')])
        proof = self.complaint.attachments.get()
        self.assertEqual((proof.source, proof.uploaded_by, proof.visibility), ('staff', self.admin, 'public'))
        response = self.client.get('/', {'reference': self.complaint.reference})
        self.assertContains(response, '<iframe')
        self.assertContains(response, reverse('complaint-evidence', args=[proof.pk]))

    def test_return_to_same_department_and_transfer_update_history_without_staff_selection(self):
        assignment = self.submit()
        transition(self.complaint.pk, self.reviewer, 'returned', internal_note='PRIVATE requested checks')
        self.assert_shared('assigned')
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, 'returned')
        self.assertIsNone(assignment.officer_id)
        transition(self.complaint.pk, self.staff, 'submit', internal_note='تم الفحص')
        transition(self.complaint.pk, self.reviewer, 'additional_assignment', department_id=self.other.pk,
                   internal_note='PRIVATE transfer reason')
        result = self.assert_shared('transferred')
        self.assertNotIn('PRIVATE', str(result))
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, 'cancelled')
        current = self.complaint.assignments.latest('assigned_at')
        self.assertEqual(current.department_id, self.other.pk)
        self.assertIsNone(current.officer_id)
        transition(self.complaint.pk, self.other_staff, 'start')
        self.assert_shared('in_progress')

    def test_reopening_revokes_publication_and_proof_until_new_review(self):
        self.submit(upload=True)
        proof = self.complaint.attachments.get()
        self.approve([proof.pk])
        transition(self.complaint.pk, self.reviewer, 'additional_assignment', department_id=self.other.pk,
                   internal_note='استكمال فحص الموقع')
        self.assert_shared('transferred')
        self.assertFalse(ComplaintPublication.objects.get(complaint=self.complaint).approved)
        self.assertNotIn('evidence', tracking_result({'reference': self.complaint.reference}))
        self.assertEqual(self.client.get(reverse('complaint-evidence', args=[proof.pk])).status_code, 200)  # admin session
        self.client.logout()
        self.assertEqual(self.client.get(reverse('complaint-evidence', args=[proof.pk])).status_code, 404)

    def test_final_decisions_require_review_confirmation_and_public_summary(self):
        self.submit()
        for values in ({'public_message': 'تم الإصلاح'}, {'confirm': True}):
            with self.assertRaises(WorkflowError):
                transition(self.complaint.pk, self.reviewer, 'approved', **values)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, 'final_review')
        self.assertFalse(self.complaint.reviews.exists())

    def test_approval_cannot_skip_department_action(self):
        self.route()
        with self.assertRaises(WorkflowError):
            self.approve()
        self.assert_shared('assigned')

    def test_closure_without_action_is_a_distinct_public_decision(self):
        transition(self.complaint.pk, self.reviewer, 'closed', internal_note='PRIVATE administrative note',
                   public_message='الطلب خارج اختصاص البلدية؛ يرجى التواصل مع الجهة المختصة.', confirm=True)
        result = self.assert_shared('closed')
        self.assertIn('خارج اختصاص البلدية', result['timeline'][-1]['public_message'])
        self.assertNotIn('PRIVATE', str(result))

    def test_department_staff_cannot_assign_review_or_work_another_department(self):
        self.route()
        for action in ('assign', 'approved', 'returned', 'publish', 'closed'):
            with self.assertRaises(PermissionDenied):
                transition(self.complaint.pk, self.staff, action, department_id=self.department.pk)
        with self.assertRaises((PermissionDenied, WorkflowError)):
            transition(self.complaint.pk, self.other_staff, 'submit', internal_note='bad')
        self.client.force_login(self.other_staff)
        self.assertEqual(self.client.get(f'/admin/complaints/complaint/{self.complaint.pk}/change/').status_code, 403)
        self.assertEqual(self.client.post(f'/staff/complaints/{self.complaint.pk}/action/', {'action': 'closed'}).status_code, 404)

    def test_invalid_evidence_does_not_save_actions_or_change_stage(self):
        self.route()
        with self.assertRaises(WorkflowError):
            transition(self.complaint.pk, self.staff, 'submit', internal_note='فحص',
                       uploads=[SimpleUploadedFile('bad.html', b'bad', content_type='text/html')])
        self.assertFalse(AssignmentAction.objects.filter(assignment__complaint=self.complaint).exists())
        self.assert_shared('assigned')

    def test_stale_action_is_rejected_without_duplicate_assignment(self):
        version = self.complaint.updated_at.isoformat()
        self.route()
        with self.assertRaises(WorkflowError) as error:
            transition(self.complaint.pk, self.admin, 'assign', department_id=self.other.pk, version=version)
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.complaint.assignments.count(), 1)

    def test_metadata_save_cannot_forge_a_review_or_reset_workflow_status(self):
        self.submit()
        self.client.force_login(self.admin)
        data = {'title': 'عنوان محدث', 'description': 'تفاصيل محدثة', 'category': '', 'location': '',
                'name': '', 'phone': '', 'email': '', 'status': 'completed',
                'reviews-0-decision': 'approved', 'reviews-0-reviewer': self.admin.pk}
        for prefix, count in [('assignments', 1), ('reviews', 0), ('attachments', 0), ('status_history', 2)]:
            data.update({f'{prefix}-TOTAL_FORMS': str(count), f'{prefix}-INITIAL_FORMS': str(count),
                         f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '0'})
            for index, record in enumerate(getattr(self.complaint, prefix).order_by('pk')):
                data[f'{prefix}-{index}-id'] = str(record.pk)
                data[f'{prefix}-{index}-complaint'] = str(self.complaint.pk)
        response = self.client.post(f'/admin/complaints/complaint/{self.complaint.pk}/change/', data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.complaint.reviews.exists())
        self.assert_shared('final_review')

    def test_public_partial_refresh_is_read_only_and_contains_latest_decision(self):
        self.submit()
        self.approve()
        count = self.complaint.status_history.count()
        response = self.client.get('/complaints/track/', {'reference': self.complaint.reference, 'partial': '1'})
        self.assertContains(response, 'tracking-result')
        self.assertContains(response, 'اكتمل إصلاح الإنارة بعد الفحص')
        self.assertNotContains(response, '<html')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(self.complaint.status_history.count(), count)

    def test_private_proof_is_served_to_reviewer_in_production_mode(self):
        self.submit(upload=True)
        proof = self.complaint.attachments.get()
        self.client.force_login(self.reviewer)
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.get(reverse('complaint-evidence', args=[proof.pk])).status_code, 200)

    def test_action_panel_accepts_multiple_proofs_and_keeps_them_internal_for_review(self):
        self.route()
        self.complaint.refresh_from_db()
        self.client.force_login(self.staff)
        response = self.client.post(reverse('complaint-transition', args=[self.complaint.pk]), {
            'action': 'submit', 'internal_note': 'فحص الموقع والصيانة',
            'version': self.complaint.updated_at.isoformat(),
            'evidence': [SimpleUploadedFile('one.png', b'one', content_type='image/png'),
                         SimpleUploadedFile('two.pdf', b'%PDF-1.4 two', content_type='application/pdf')],
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.complaint.attachments.filter(source='staff', uploaded_by=self.staff, visibility='internal').count(), 2)
        self.assertNotIn('evidence', tracking_result({'reference': self.complaint.reference}))

    def test_preview_is_lightweight_and_has_the_same_access_rules_as_original(self):
        from io import BytesIO
        from PIL import Image
        self.submit()
        data = BytesIO()
        Image.new('RGB', (1800, 1200), 'green').save(data, 'PNG')
        proof = ComplaintAttachment.objects.create(complaint=self.complaint, source='staff',
            file=SimpleUploadedFile('large.png', data.getvalue(), content_type='image/png'), original_name='large.png')
        url = reverse('complaint-evidence', args=[proof.pk]) + '?preview=1'
        self.assertEqual(self.client.get(url).status_code, 404)
        self.approve([proof.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/webp')
        image = Image.open(BytesIO(response.content))
        self.assertLessEqual(max(image.size), 960)

    def test_legacy_approved_record_repairs_stage_without_publishing_private_reason(self):
        assignment = self.route()
        self.complaint.status = 'final_review'
        self.complaint.save()
        ComplaintReview.objects.create(complaint=self.complaint, assignment=assignment, reviewer=self.admin,
                                      decision='approved', reason='PRIVATE historic note')
        migration = importlib.import_module('complaints.migrations.0008_reconcile_workflow')
        migration.reconcile(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        result = self.assert_shared('completed')
        self.assertNotIn('PRIVATE', str(result))
        self.assertFalse(ComplaintPublication.objects.filter(complaint=self.complaint).exists())

    def test_old_approval_does_not_override_later_department_transfer(self):
        assignment = self.submit()
        self.approve()
        review = self.complaint.reviews.get()
        ComplaintReview.objects.filter(pk=review.pk).update(created_at=timezone.now() - timedelta(days=1))
        transition(self.complaint.pk, self.reviewer, 'additional_assignment', department_id=self.other.pk, internal_note='فحص آخر')
        migration = importlib.import_module('complaints.migrations.0008_reconcile_workflow')
        migration.reconcile(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        self.assert_shared('transferred')

    def test_legacy_close_after_staff_action_is_not_relabelled_as_unprocessed(self):
        assignment = self.submit()
        self.complaint.status = 'completed'
        self.complaint.save()
        ComplaintReview.objects.create(complaint=self.complaint, assignment=assignment,
                                      reviewer=self.admin, decision='closed', reason='اكتملت الصيانة')
        migration = importlib.import_module('complaints.migrations.0008_reconcile_workflow')
        migration.reconcile(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        self.assert_shared('completed')
