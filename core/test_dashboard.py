from django.contrib.auth.models import User
from django.test import TestCase

from complaints.admin import AssignmentForm, ReviewForm
from complaints.models import Complaint, ComplaintAssignment
from core.models import Department


class CouncilDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('council-admin', password='test-password')
        self.complaint = Complaint.objects.create(reference='YBC-TEST-1', title='إنارة الشارع', description='تفاصيل', tracking_hash='unused')

    def test_dashboard_shows_real_data_and_work_forms(self):
        self.client.force_login(self.admin)
        response = self.client.get('/admin/')
        self.assertContains(response, 'YBC-TEST-1')
        self.assertEqual(response.context['metrics'][0]['value'], 1)
        self.assertContains(response, '/admin/complaints/complaintassignment/add/')
        self.assertEqual(self.client.get('/admin/complaints/complaintassignment/add/').status_code, 200)
        self.assertEqual(self.client.get('/admin/complaints/complaintreview/add/').status_code, 200)

    def test_staff_without_model_permissions_cannot_see_complaints(self):
        user = User.objects.create_user('limited', is_staff=True)
        self.client.force_login(user)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'YBC-TEST-1')
        self.assertEqual(response.context['metrics'], [])

    def test_assignment_rejects_officer_outside_department(self):
        department = Department.objects.create(name='الطرق')
        officer = User.objects.create_user('officer', is_staff=True)
        data = {'complaint': self.complaint.pk, 'department': department.pk, 'officer': officer.pk, 'status': 'assigned', 'priority': 'medium'}
        form = AssignmentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('officer', form.errors)
        department.members.add(officer)
        self.assertTrue(AssignmentForm(data=data).is_valid())

    def test_review_rejects_assignment_from_another_complaint(self):
        other = Complaint.objects.create(reference='YBC-TEST-2', title='أخرى', description='تفاصيل', tracking_hash='unused')
        department = Department.objects.create(name='الطرق')
        assignment = ComplaintAssignment.objects.create(complaint=other, department=department)
        form = ReviewForm(data={'complaint': self.complaint.pk, 'assignment': assignment.pk, 'reviewer': self.admin.pk, 'decision': 'approved'})
        self.assertFalse(form.is_valid())
        self.assertIn('assignment', form.errors)
