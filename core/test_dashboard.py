from datetime import timedelta

from django.utils import timezone
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
        self.assertContains(response, '/admin/complaints/complaint/')
        self.assertRedirects(self.client.get('/admin/complaints/complaintassignment/add/'), '/admin/complaints/complaint/')
        self.assertEqual(self.client.get('/admin/complaints/complaintreview/add/').status_code, 403)

    def test_staff_without_model_permissions_cannot_see_complaints(self):
        user = User.objects.create_user('limited', is_staff=True)
        self.client.force_login(user)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'YBC-TEST-1')
        self.assertEqual(response.context['metrics'], [])

    def test_staff_followup_columns_and_charts_use_only_visible_assignments(self):
        officer = User.objects.create_user('scoped-officer', is_staff=True)
        visible_department = Department.objects.create(name='الإنارة')
        hidden_department = Department.objects.create(name='قسم خارج النطاق')
        visible_department.members.add(officer)
        now = timezone.now()
        ComplaintAssignment.objects.create(
            complaint=self.complaint, department=visible_department,
            priority='high', due_at=now - timedelta(hours=1),
        )
        ComplaintAssignment.objects.create(
            complaint=self.complaint, department=hidden_department,
            priority='urgent', due_at=now - timedelta(days=2),
        )
        ComplaintAssignment.objects.create(
            complaint=self.complaint, department=visible_department,
            priority='urgent', status='approved', due_at=now - timedelta(days=3),
        )
        self.client.force_login(officer)
        response = self.client.get('/admin/complaints/complaint/')
        self.assertContains(response, 'مرتفعة')
        self.assertContains(response, 'متأخرة')
        self.assertNotContains(response, 'class="followup-badge followup-badge--urgent"')
        attention_url = '/admin/complaints/complaint/?attention='
        self.assertNotContains(self.client.get(attention_url + 'urgent'), self.complaint.reference)
        self.assertContains(self.client.get(attention_url + 'overdue'), self.complaint.reference)
        response = self.client.get('/staff/dashboard/')
        self.assertContains(response, 'الأولوية')
        self.assertContains(response, 'متأخرة')
        self.assertNotContains(response, hidden_department.name)

        response = self.client.get('/admin/')
        charts = {chart['variant']: chart['rows'] for chart in response.context['dashboard_charts']}
        status, weeks, overdue = (charts[key] for key in ('status', 'weekly', 'overdue'))
        self.assertContains(response, 'complaint-chart--weekly')
        self.assertEqual(sum(row['count'] for row in status), 1)
        self.assertEqual(sum(row['count'] for row in weeks), 1)
        self.assertEqual([(row['label'], row['count']) for row in overdue], [(visible_department.name, 1)])

    def test_department_manager_can_change_priority_for_own_open_assignment(self):
        from django.contrib.auth.models import Group
        from django.core.exceptions import PermissionDenied
        from django.urls import reverse

        from complaints.workflow import transition
        from core.models import AuditLog

        manager = User.objects.create_user('department-lead', is_staff=True)
        manager.groups.add(Group.objects.create(name='Department Manager'))
        own_department = Department.objects.create(name='الطرقات')
        own_department.members.add(manager)
        other_department = Department.objects.create(name='المياه')
        own = ComplaintAssignment.objects.create(complaint=self.complaint, department=own_department)
        other = ComplaintAssignment.objects.create(complaint=self.complaint, department=other_department)
        prior_status = self.complaint.status

        self.client.force_login(manager)
        page = self.client.get(reverse('admin:complaints_complaint_change', args=[self.complaint.pk]))
        self.assertContains(page, 'تغيير أولوية الإحالة')
        response = self.client.post(reverse('complaint-transition', args=[self.complaint.pk]), {
            'action': 'update_priority', 'priority_assignment': own.pk, 'priority': 'urgent',
            'version': self.complaint.updated_at.isoformat(),
        })
        self.assertEqual(response.status_code, 302)
        own.refresh_from_db()
        self.complaint.refresh_from_db()
        self.assertEqual(own.priority, 'urgent')
        self.assertEqual(self.complaint.status, prior_status)
        self.assertEqual(AuditLog.objects.get(target_id=str(own.pk)).metadata['previous'], 'medium')
        self.assertContains(self.client.get('/admin/complaints/complaint/?attention=urgent'), self.complaint.reference)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/admin/complaints/complaint/?attention=urgent'), self.complaint.reference)

        newer = Complaint.objects.create(reference='YBC-TEST-NEW', title='بلاغ حديث', description='تفاصيل')
        listing = self.client.get('/admin/complaints/complaint/')
        self.assertEqual([row.pk for row in listing.context['cl'].result_list][:2], [self.complaint.pk, newer.pk])

        with self.assertRaises(PermissionDenied):
            transition(self.complaint.pk, manager, 'update_priority', assignment_id=other.pk, priority='urgent')

    def test_complaint_detail_groups_actions_and_records_in_order(self):
        self.client.force_login(self.admin)
        response = self.client.get(f'/admin/complaints/complaint/{self.complaint.pk}/change/')
        self.assertContains(response, 'complaint-summary')
        html = response.content.decode()
        positions = [
            html.index(f'id="{section}"')
            for section in (
                'complaint-summary-title', 'complaint-next-action', 'complaint-information',
                'complaint-assignments', 'complaint-team-work', 'complaint-history',
                'complaint-private-details',
            )
        ]
        self.assertEqual(positions, sorted(positions))
        for management_field in ('assignments', 'attachments', 'reviews', 'status_history'):
            self.assertContains(response, f'name="{management_field}-TOTAL_FORMS"')

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

    def test_assignment_uses_compact_choices_and_saves_native_datetime(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from django import forms
        department = Department.objects.create(name='النظافة')
        department.members.add(self.admin)
        request = RequestFactory().get('/admin/complaints/complaintassignment/add/')
        request.user = self.admin
        form_class = admin.site._registry[ComplaintAssignment].get_form(request)
        form = form_class(data={
            'complaint': self.complaint.pk, 'department': department.pk,
            'officer': self.admin.pk, 'priority': 'high', 'status': 'assigned',
            'due_at': '2026-11-01T10:30',
        })
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save()
        self.assertEqual(assignment.due_at.hour, 10)
        for name in ['priority', 'status', 'department']:
            widget = form.fields[name].widget
            self.assertIsInstance(getattr(widget, 'widget', widget), forms.Select)
        officer_widget = form.fields['officer'].widget
        self.assertIsInstance(getattr(officer_widget, 'widget', officer_widget), forms.HiddenInput)
        self.client.force_login(self.admin)
        response = self.client.get('/admin/core/department/')
        self.assertContains(response, 'core/dashboard.')
        self.assertContains(response, 'core/fonts.')

    def test_every_dashboard_page_uses_shared_theme_and_accessible_account_controls(self):
        self.client.force_login(self.admin)
        for path in (
            '/admin/', '/admin/core/department/', '/admin/auth/user/',
            '/admin/auth/user/add/', '/admin/website/page/add/',
            '/admin/website/newsarticle/add/',
            f'/admin/complaints/complaint/{self.complaint.pk}/change/',
            '/staff/reports/',
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'core/fonts.')
                self.assertContains(response, 'core/dashboard.')
                self.assertContains(response, 'id="dashboard-account-menu"')
                self.assertContains(response, 'class="dashboard-logout"')
                self.assertContains(response, 'id="dashboard-theme-button"')
                self.assertNotContains(response, 'light_mode')
                self.assertNotContains(response, 'Type to search')
                self.assertNotContains(response, '<title> </title>')
                if path == '/admin/website/newsarticle/add/':
                    self.assertContains(response, 'placeholder="التاريخ"')
                    self.assertContains(response, 'placeholder="الوقت"')
                    self.assertContains(response, 'aria-label="اختر ملفاً للرفع"')
