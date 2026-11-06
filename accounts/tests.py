from django.contrib.auth.models import Permission, User
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
