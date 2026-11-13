from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase

from core.models import Department


class StaffAccountAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('staff-admin', password='test-password')
        cls.department = Department.objects.create(name='الطرق والإنارة')
        cls.other_department = Department.objects.create(name='النظافة والبيئة')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_admin_creation_saves_the_selected_role_and_departments(self):
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'new-officer', 'first_name': 'أحمد', 'last_name': 'خالد',
            'email': 'officer@example.com', 'password1': 'A8!council-pass',
            'password2': 'A8!council-pass', 'role': 'staff',
            'departments': [self.department.pk], 'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='new-officer')
        self.assertTrue(user.check_password('A8!council-pass'))
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(list(user.groups.values_list('name', flat=True)), ['Department Officer'])
        self.assertEqual(list(user.council_departments.all()), [self.department])

    def test_admin_update_saves_role_and_department_changes_without_changing_password(self):
        user = User.objects.create_user('existing-officer', password='preserved-password', is_staff=True)
        user.council_departments.add(self.department)
        response = self.client.post(f'/admin/auth/user/{user.pk}/change/', {
            'username': user.username, 'first_name': 'ليلى', 'last_name': 'حسن',
            'email': 'reviewer@example.com', 'role': 'reviewer',
            'departments': [self.other_department.pk], 'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('preserved-password'))
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(list(user.groups.values_list('name', flat=True)), ['Complaint Reviewer'])
        self.assertEqual(list(user.council_departments.all()), [self.other_department])

    def test_change_form_offers_password_change_without_rendering_hash_metadata(self):
        response = self.client.get(f'/admin/auth/user/{self.admin.pk}/change/')
        self.assertContains(response, 'تغيير كلمة المرور')
        self.assertNotContains(response, 'pbkdf2_sha256')
        self.assertNotContains(response, 'Raw passwords are not stored')

    def test_view_only_staff_can_read_assignments_without_editing_them(self):
        viewer = User.objects.create_user('account-viewer', is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename='view_user', content_type__app_label='auth'))
        self.admin.council_departments.add(self.department)
        self.client.force_login(viewer)
        path = f'/admin/auth/user/{self.admin.pk}/change/'
        response = self.client.get(path)
        self.assertContains(response, self.department.name)
        self.assertContains(response, 'مشرف عام')
        self.assertNotContains(response, '../password/')
        self.assertNotContains(response, 'name="_save"')
        self.assertEqual(self.client.post(path, {'role': 'staff'}).status_code, 403)

    def test_department_roles_require_a_department_when_creating_an_account(self):
        for role in ('staff', 'supervisor'):
            with self.subTest(role=role):
                response = self.client.post('/admin/auth/user/add/', {
                    'username': 'missing-department-' + role,
                    'password1': 'A8!council-pass', 'password2': 'A8!council-pass',
                    'role': role, 'is_active': 'on',
                })
                self.assertContains(response, 'حدد قسم الموظف قبل حفظ الحساب.')
                self.assertFalse(User.objects.filter(username='missing-department-' + role).exists())

    def test_demoting_a_user_replaces_old_roles_departments_and_direct_permissions(self):
        from complaints.models import Complaint, ComplaintAssignment
        from complaints.workflow import can_review
        user = User.objects.create_superuser('demoted-staff', password='preserved-password')
        user.groups.add(Group.objects.create(name='Complaint Reviewer'))
        user.user_permissions.add(*Permission.objects.all())
        user.council_departments.add(self.other_department)
        own = Complaint.objects.create(reference='NEW-DEPARTMENT', title='Own case', description='Own case')
        other = Complaint.objects.create(reference='OLD-DEPARTMENT', title='Other case', description='Other case')
        ComplaintAssignment.objects.create(complaint=own, department=self.department)
        ComplaintAssignment.objects.create(complaint=other, department=self.other_department)
        response = self.client.post(f'/admin/auth/user/{user.pk}/change/', {
            'username': user.username, 'role': 'staff',
            'departments': [self.department.pk], 'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertFalse(can_review(user))
        self.assertTrue(user.check_password('preserved-password'))
        self.assertEqual(list(user.groups.values_list('name', flat=True)), ['Department Officer'])
        self.assertEqual(list(user.council_departments.all()), [self.department])
        self.assertFalse(user.user_permissions.exists())
        self.client.force_login(user)
        response = self.client.get('/admin/complaints/complaint/')
        self.assertContains(response, own.reference)
        self.assertNotContains(response, other.reference)
        self.assertEqual(self.client.post(f'/admin/auth/user/{user.pk}/change/', {
            'username': user.username, 'role': 'superadmin', 'is_active': 'on',
        }).status_code, 403)

    def test_legacy_user_and_group_grants_cannot_be_used_to_escalate_a_staff_role(self):
        user = User.objects.create_user('legacy-account-manager', is_staff=True)
        group = Group.objects.create(name='Department Officer')
        user.groups.add(group)
        user.council_departments.add(self.department)
        user.user_permissions.add(*Permission.objects.filter(content_type__app_label='auth'))
        self.client.force_login(user)
        for path, data in (
            ('/admin/auth/user/add/', {'username': 'rogue-admin', 'role': 'superadmin'}),
            (f'/admin/auth/user/{user.pk}/change/', {'username': user.username, 'role': 'superadmin'}),
            (f'/admin/auth/user/{self.admin.pk}/delete/', {'post': 'yes'}),
            (f'/admin/auth/user/{self.admin.pk}/password/', {'password1': 'A8!council-pass', 'password2': 'A8!council-pass'}),
            ('/admin/auth/group/add/', {'name': 'Complaint Reviewer'}),
            (f'/admin/auth/group/{group.pk}/change/', {'name': 'Complaint Reviewer'}),
            (f'/admin/auth/group/{group.pk}/delete/', {'post': 'yes'}),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, data).status_code, 403)
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertFalse(User.objects.filter(username='rogue-admin').exists())

    def test_reviewer_role_can_be_created_without_a_department(self):
        from complaints.workflow import can_review
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'new-reviewer', 'password1': 'A8!council-pass',
            'password2': 'A8!council-pass', 'role': 'reviewer', 'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='new-reviewer')
        self.assertTrue(can_review(user))
        self.assertFalse(user.is_superuser)

    def test_mixed_legacy_groups_display_the_restricted_department_role(self):
        from django.contrib import admin
        from .admin import SimpleUserChangeForm
        user = User.objects.create_user('mixed-role-staff', is_staff=True)
        for name in ('Department Officer', 'Complaint Reviewer'):
            user.groups.add(Group.objects.get_or_create(name=name)[0])
        self.assertEqual(SimpleUserChangeForm(instance=user).initial['role'], 'staff')
        self.assertEqual(admin.site._registry[User].role(user), 'موظف قسم')
