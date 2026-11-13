import tempfile
from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Department
from .models import (
    AssignmentAction, Complaint, ComplaintAssignment, ComplaintAttachment,
    ComplaintReview, ComplaintStatusHistory, InternalNotification,
)
from .workflow import available_actions, can_review, complaints_for, transition


class DepartmentComplaintAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('access-admin', password='test-password')
        cls.officer = User.objects.create_user('access-officer', is_staff=True)
        cls.officer.groups.add(Group.objects.create(name='Department Officer'))
        # Old direct/model grants must not turn a department account into a reviewer.
        cls.officer.user_permissions.add(*Permission.objects.filter(content_type__app_label='complaints'))
        cls.reviewer = User.objects.create_user('access-reviewer', is_staff=True)
        cls.reviewer.groups.add(Group.objects.create(name='Complaint Reviewer'))
        cls.own_department = Department.objects.create(name='قسم الإنارة')
        cls.other_department = Department.objects.create(name='قسم النظافة')
        cls.own_department.members.add(cls.officer)
        cls.own = Complaint.objects.create(reference='OWN-CASE', title='OWN TITLE', description='OWN DETAILS', status='assigned')
        cls.other = Complaint.objects.create(reference='OTHER-CASE', title='OTHER TITLE', description='OTHER DETAILS', status='assigned')
        cls.unassigned = Complaint.objects.create(reference='UNASSIGNED-CASE', title='NEW TITLE', description='NEW DETAILS')
        deadline = timezone.now() - timedelta(days=1)
        cls.own_assignment = ComplaintAssignment.objects.create(complaint=cls.own, department=cls.own_department, due_at=deadline)
        cls.other_assignment = ComplaintAssignment.objects.create(complaint=cls.other, department=cls.other_department, due_at=deadline)

    def setUp(self):
        self.client.force_login(self.officer)

    def test_legacy_permissions_do_not_grant_global_review_authority(self):
        self.assertFalse(can_review(self.officer))
        self.assertSetEqual(set(complaints_for(self.officer)), {self.own})
        self.assertEqual(available_actions(self.officer, self.other), [])
        self.assertEqual(available_actions(self.officer, self.own), ['start', 'note', 'submit'])

    def test_lists_dashboard_search_reports_and_autocomplete_stay_in_department(self):
        for path in ('/admin/', '/admin/complaints/complaint/', '/staff/dashboard/', '/staff/reports/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertContains(response, self.own.reference)
                self.assertNotContains(response, self.other.reference)
                self.assertNotContains(response, self.unassigned.reference)
        self.assertNotContains(self.client.get('/admin/complaints/complaint/', {'q': 'OTHER'}), self.other.reference)
        response = self.client.get('/staff/review-queue/')
        self.assertEqual([item['id'] for item in response.json()['complaints']], [self.own.pk])
        response = self.client.get('/admin/autocomplete/', {
            'app_label': 'complaints', 'model_name': 'complaintattachment',
            'field_name': 'complaint', 'term': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()['results']], [str(self.own.pk)])
        report = self.client.get('/staff/reports/')
        self.assertEqual(report.context['total_complaints'], 1)
        self.assertEqual(report.context['total_assignments'], 1)
        self.assertEqual(report.context['overdue_count'], 1)
        self.assertEqual(list(report.context['departments']), [self.own_department])

    def test_foreign_case_details_and_forged_updates_are_denied(self):
        path = reverse('admin:complaints_complaint_change', args=[self.other.pk])
        response = self.client.get(path)
        self.assertNotContains(response, self.other.description, status_code=response.status_code)
        response = self.client.post(path, {'title': 'FORGED', 'description': 'FORGED'})
        self.assertNotEqual(response.status_code, 200)
        for action in ('start', 'submit', 'assign', 'approved', 'closed', 'publish', 'additional_assignment'):
            with self.subTest(action=action):
                response = self.client.post(reverse('complaint-transition', args=[self.other.pk]), {
                    'action': action, 'version': self.other.updated_at.isoformat(),
                    'internal_note': 'FORGED', 'public_message': 'FORGED',
                    'department': self.own_department.pk, 'confirm': 'on',
                })
                self.assertEqual(response.status_code, 404)
                with self.assertRaises(PermissionDenied):
                    transition(self.other.pk, self.officer, action,
                               assignment_id=self.other_assignment.pk, department_id=self.own_department.pk,
                               internal_note='FORGED', public_message='FORGED', confirm=True)
        self.other.refresh_from_db()
        self.assertEqual(self.other.status, 'assigned')
        self.assertEqual(self.other.title, 'OTHER TITLE')
        self.assertFalse(AssignmentAction.objects.exists())
        self.assertFalse(ComplaintReview.objects.exists())
        self.assertFalse(ComplaintStatusHistory.objects.exists())

    def test_legacy_action_endpoints_cannot_bypass_department_scope(self):
        for path, data in (
            ('/staff/assign/', {'complaint_id': self.other.pk, 'department_id': self.own_department.pk}),
            ('/staff/action/', {'assignment_id': self.other_assignment.pk, 'internal_action': 'FORGED'}),
            ('/staff/final-review/', {'complaint_id': self.other.pk, 'decision': 'closed', 'summary': 'FORGED', 'confirm': 'on'}),
            ('/staff/publish/', {'complaint_id': self.other.pk, 'summary': 'FORGED', 'confirm': 'on'}),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, data).status_code, 403)

    def test_staff_can_work_own_case_but_not_edit_metadata_review_or_delete_it(self):
        self.assertContains(self.client.get(reverse('admin:complaints_complaint_change', args=[self.own.pk])), self.own.description)
        self.assertEqual(self.client.post(reverse('admin:complaints_complaint_change', args=[self.own.pk]), {'title': 'FORGED'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:complaints_complaint_delete', args=[self.own.pk]), {'post': 'yes'}).status_code, 403)
        for action in ('assign', 'approved', 'closed', 'publish', 'returned', 'additional_assignment'):
            with self.subTest(action=action), self.assertRaises(PermissionDenied):
                transition(self.own.pk, self.officer, action)
        transition(self.own.pk, self.officer, 'start')
        transition(self.own.pk, self.officer, 'submit', internal_note='تم الإصلاح')
        self.own.refresh_from_db()
        self.assertEqual(self.own.status, 'final_review')

    def test_old_named_officer_assignment_does_not_override_department_membership(self):
        self.other_assignment.officer = self.officer
        self.other_assignment.save()
        self.assertNotIn(self.other, complaints_for(self.officer))
        self.assertEqual(available_actions(self.officer, self.other), [])
        self.assertNotContains(self.client.get('/staff/dashboard/'), self.other.reference)
        self.assertEqual(self.client.post('/staff/action/', {
            'assignment_id': self.other_assignment.pk, 'internal_action': 'FORGED',
        }).status_code, 403)

    def test_transfer_removes_old_department_access_and_notifications(self):
        InternalNotification.objects.create(user=self.officer, complaint=self.own, message='OLD CASE NOTIFICATION')
        transition(self.own.pk, self.reviewer, 'additional_assignment',
                   department_id=self.other_department.pk, internal_note='يتطلب متابعة النظافة')
        self.assertFalse(complaints_for(self.officer).exists())
        self.assertEqual(available_actions(self.officer, self.own), [])
        for path in ('/admin/', '/staff/dashboard/', '/staff/reports/'):
            response = self.client.get(path)
            self.assertNotContains(response, self.own.reference)
            self.assertNotContains(response, 'OLD CASE NOTIFICATION')

    def test_department_changes_and_inactive_departments_revoke_access(self):
        self.own_department.active = False
        self.own_department.save()
        self.assertFalse(complaints_for(self.officer).exists())
        self.assertEqual(available_actions(self.officer, self.own), [])
        self.own_department.active = True
        self.own_department.save()
        self.own_department.members.remove(self.officer)
        self.other_department.members.add(self.officer)
        self.assertSetEqual(set(complaints_for(self.officer)), {self.other})
        self.assertEqual(available_actions(self.officer, self.own), [])

    def test_private_evidence_uses_same_department_scope(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            own = ComplaintAttachment.objects.create(complaint=self.own, file=SimpleUploadedFile('own.png', b'own-private'))
            other = ComplaintAttachment.objects.create(complaint=self.other, file=SimpleUploadedFile('other.png', b'other-private'))
            response = self.client.get(reverse('complaint-evidence', args=[own.pk]))
            self.assertEqual(response.status_code, 200)
            response.close()
            for query in ('', '?preview=1'):
                self.assertEqual(self.client.get(reverse('complaint-evidence', args=[other.pk]) + query).status_code, 404)

    def test_multiple_department_memberships_and_global_reviewers(self):
        self.other_department.members.add(self.officer)
        self.assertSetEqual(set(complaints_for(self.officer)), {self.own, self.other})
        for user in (self.reviewer, self.admin):
            self.assertTrue(can_review(user))
            self.assertSetEqual(set(complaints_for(user)), {self.own, self.other, self.unassigned})

    def test_staff_without_a_department_has_no_complaint_access(self):
        self.own_department.members.remove(self.officer)
        self.assertFalse(complaints_for(self.officer).exists())
        for path in ('/admin/', '/staff/dashboard/', '/staff/reports/'):
            response = self.client.get(path)
            for complaint in (self.own, self.other, self.unassigned):
                self.assertNotContains(response, complaint.reference)

    def test_shared_cases_do_not_allow_actions_on_another_departments_assignment(self):
        shared_assignment = ComplaintAssignment.objects.create(
            complaint=self.own, department=self.other_department, due_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.post('/staff/action/', {
            'assignment_id': shared_assignment.pk, 'internal_action': 'FORGED',
        })
        self.assertEqual(response.status_code, 403)
        report = self.client.get('/staff/reports/')
        self.assertEqual(report.context['total_assignments'], 1)
        self.assertEqual(report.context['overdue_count'], 1)
        transition(self.own.pk, self.officer, 'submit', internal_note='إجراء قسم الإنارة')
        self.own.refresh_from_db()
        self.assertEqual(self.own.status, 'in_progress')
        self.assertEqual(available_actions(self.officer, self.own), [])
        self.assertFalse(AssignmentAction.objects.filter(assignment=shared_assignment).exists())

    def test_a_department_officer_role_cannot_inherit_review_authority_from_an_extra_group(self):
        self.officer.groups.add(Group.objects.get(name='Complaint Reviewer'))
        self.assertFalse(can_review(self.officer))
        self.assertSetEqual(set(complaints_for(self.officer)), {self.own})

    def test_inactive_and_nonstaff_accounts_cannot_use_workflow_helpers(self):
        for field in ('is_active', 'is_staff'):
            with self.subTest(field=field):
                setattr(self.officer, field, False)
                self.assertFalse(can_review(self.officer))
                self.assertFalse(complaints_for(self.officer).exists())
                self.assertEqual(available_actions(self.officer, self.own), [])
                with self.assertRaises(PermissionDenied):
                    transition(self.own.pk, self.officer, 'start')
                setattr(self.officer, field, True)

    def test_old_notifications_and_recovery_records_cannot_leak_foreign_cases(self):
        from .models import RecoveryRequest
        InternalNotification.objects.create(user=self.officer, complaint=self.own, message='OWN NOTIFICATION')
        InternalNotification.objects.create(user=self.officer, complaint=self.other, message='FOREIGN NOTIFICATION')
        InternalNotification.objects.create(user=self.admin, complaint=self.own, message='OTHER USER NOTIFICATION')
        RecoveryRequest.objects.create(complaint_reference=self.own.reference, explanation='Own recovery')
        RecoveryRequest.objects.create(complaint_reference=self.other.reference, explanation='Other recovery')
        response = self.client.get('/admin/complaints/internalnotification/')
        self.assertContains(response, 'OWN NOTIFICATION')
        self.assertNotContains(response, 'FOREIGN NOTIFICATION')
        self.assertNotContains(response, 'OTHER USER NOTIFICATION')
        response = self.client.get('/admin/complaints/recoveryrequest/')
        self.assertContains(response, self.own.reference)
        self.assertNotContains(response, self.other.reference)
