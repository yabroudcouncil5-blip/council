from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client, override_settings
from .models import Complaint, ComplaintStatusHistory, RecoveryRequest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from core.models import Department, ComplaintCategory

class ComplaintFlowTests(TestCase):
    def test_anonymous_submission_and_reference_tracking(self):
        client = Client()
        response = client.post('/api/complaints/', {'title':'إنارة','description':'الشارع مظلم'})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(client.post('/api/complaints/track/', {'reference':data['reference']}).status_code, 200)
        self.assertEqual(client.post('/api/complaints/track/', {'reference':'YBC-0000-000000'}).status_code, 404)
        self.assertNotIn('tracking_code', data)
        self.assertEqual(Complaint.objects.count(), 1)

    def test_recovery_request_requires_explanation(self):
        client = Client()
        self.assertEqual(client.post('/api/complaints/recovery/', {}).status_code, 400)
        self.assertEqual(client.post('/api/complaints/recovery/', {'explanation':'الشكوى عن إنارة قرب المدرسة'}).status_code, 201)
        self.assertEqual(RecoveryRequest.objects.count(), 1)

    def test_invalid_email_and_large_upload_are_rejected(self):
        client = Client()
        self.assertEqual(client.post('/api/complaints/', {'title':'x','description':'y','email':'bad'}).status_code, 400)
        upload = SimpleUploadedFile('x.exe', b'bad', content_type='application/x-msdownload')
        self.assertEqual(client.post('/api/complaints/', {'title':'x','description':'y','photo':upload}).status_code, 400)

    def test_staff_action_evidence_is_saved_for_supervisor_review(self):
        from .models import ComplaintAssignment, AssignmentAction, ComplaintAttachment
        user = User.objects.create_user('evidence-staff', password='pass', is_staff=True)
        department = Department.objects.create(name='الإنارة')
        department.members.add(user)
        complaint = Complaint.objects.create(reference='YBC-2026-900002', title='عطل', description='تفاصيل', tracking_hash='unused')
        assignment = ComplaintAssignment.objects.create(complaint=complaint, department=department, officer=user)
        client = Client(); client.force_login(user)
        evidence = SimpleUploadedFile('proof.jpg', b'image-data', content_type='image/jpeg')
        response = client.post('/staff/action/', {'assignment_id': assignment.id, 'internal_action': 'تم الإصلاح', 'evidence': evidence})
        self.assertEqual(response.status_code, 201)
        attachment = ComplaintAttachment.objects.get(complaint=complaint)
        self.assertEqual((attachment.source, attachment.visibility, attachment.uploaded_by), ('staff', 'internal', user))
        self.assertEqual(AssignmentAction.objects.filter(assignment=assignment).count(), 1)

    def test_multi_department_assignment_and_closure_guard(self):
        from .workflow import transition, WorkflowError
        user = User.objects.create_superuser('multi-reviewer', password='test-password')
        complaint = Complaint.objects.create(reference='YBC-MULTI-1', title='خدمة', description='تفاصيل')
        d1 = Department.objects.create(name='طرق')
        d2 = Department.objects.create(name='إنارة')
        _, a1 = transition(complaint.pk, user, 'assign', department_id=d1.pk)
        _, a2 = transition(complaint.pk, user, 'assign', department_id=d2.pk)
        transition(complaint.pk, user, 'submit', assignment_id=a1.pk, internal_note='أصلح الطريق')
        transition(complaint.pk, user, 'submit', assignment_id=a2.pk, internal_note='أصلحت الإنارة')
        transition(complaint.pk, user, 'approved', assignment_id=a1.pk, public_message='تم الإصلاح', confirm=True)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'final_review')
        with self.assertRaises(WorkflowError):
            transition(complaint.pk, user, 'publish', public_message='تم الإصلاح', confirm=True)
        transition(complaint.pk, user, 'approved', assignment_id=a2.pk, public_message='اكتمل العمل', confirm=True)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'completed')

    def test_public_resolutions_only_include_approved_completed_items(self):
        from .models import ComplaintPublication
        complaint = Complaint.objects.create(reference='YBC-PUBLIC-1', title='خدمة', description='تفاصيل', status='completed')
        publication = ComplaintPublication.objects.create(complaint=complaint, approved=True, visibility='public', summary='تم الحل')
        self.assertEqual(len(self.client.get('/api/public/resolutions/').json()['results']), 1)
        publication.approved = False
        publication.save()
        self.assertEqual(self.client.get('/api/public/resolutions/').json()['results'], [])

    def test_current_stage_is_shared_even_before_legacy_result_is_published(self):
        from .models import ComplaintPublication
        complaint = Complaint.objects.create(reference='YBC-2026-900001', title='إنارة', description='تفاصيل', status='completed')
        ComplaintStatusHistory.objects.create(complaint=complaint, status='completed', public_message='تمت المعالجة')
        before = self.client.get('/api/complaints/track/', {'reference': complaint.reference}).json()
        self.assertEqual(before['status'], complaint.get_status_display())
        self.assertEqual(before['timeline'][-1]['status_code'], complaint.status)
        staff = User.objects.create_user('staff-publisher', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.post('/staff/publish/', {'complaint_id': complaint.pk, 'summary': 'تم الحل', 'confirm': 'on'}).status_code, 403)
        reviewer = User.objects.create_superuser('publisher', password='test-password')
        self.client.force_login(reviewer)
        self.assertEqual(self.client.post('/staff/publish/', {'complaint_id': complaint.pk, 'summary': 'تم الحل', 'confirm': 'on'}).status_code, 201)
        self.assertEqual(ComplaintPublication.objects.get(complaint=complaint).approved_by, reviewer)
        self.assertEqual(self.client.get('/api/complaints/track/', {'reference': complaint.reference}).json()['timeline'][-1]['public_message'], 'تم الحل')

    def test_staff_report_is_protected(self):
        self.assertEqual(Client().get('/staff/reports/').status_code, 302)

    def test_staff_dashboard_requires_staff(self):
        user=User.objects.create_user('resident',password='pass'); client=Client(); client.force_login(user); self.assertEqual(client.get('/staff/dashboard/').status_code, 403)


class ComplaintAdminNavigationTests(TestCase):
    def test_old_workspace_uses_the_normal_complaint_pages(self):
        user = User.objects.create_superuser('workspace-admin', password='test-password')
        complaint = Complaint.objects.create(reference='YBC-WORKSPACE-1', title='إنارة', description='تفاصيل')
        self.client.force_login(user)
        self.assertRedirects(self.client.get('/staff/complaints/'), '/admin/complaints/complaint/', fetch_redirect_response=False)
        self.assertRedirects(
            self.client.get('/staff/complaints/', {'complaint': complaint.pk}),
            f'/admin/complaints/complaint/{complaint.pk}/change/', fetch_redirect_response=False,
        )

    def test_department_staff_dashboard_includes_department_level_assignments(self):
        from .models import ComplaintAssignment
        user = User.objects.create_user('department-dashboard-staff', is_staff=True)
        department = Department.objects.create(name='خدمات الحي')
        department.members.add(user)
        complaint = Complaint.objects.create(reference='YBC-DEPARTMENT-1', title='إنارة', description='تفاصيل', status='assigned')
        ComplaintAssignment.objects.create(complaint=complaint, department=department)
        self.client.force_login(user)
        response = self.client.get('/staff/dashboard/')
        self.assertContains(response, complaint.reference)
        self.assertContains(response, complaint.get_status_display())
        self.assertContains(response, 'dashboard-account-menu')
        self.assertContains(response, f'/admin/complaints/complaint/{complaint.pk}/change/')

    def test_complaint_action_panel_saves_deadline_review_and_publication(self):
        from .models import ComplaintAssignment, AssignmentAction, ComplaintPublication
        from django.utils import timezone
        user = User.objects.create_superuser('panel-admin', password='test-password')
        complaint = Complaint.objects.create(reference='YBC-INLINE-1', title='إنارة', description='تفاصيل')
        department = Department.objects.create(name='الإنارة')
        self.client.force_login(user)
        url = f'/staff/complaints/{complaint.pk}/action/'
        def post(action, **values):
            complaint.refresh_from_db()
            return self.client.post(url, {'action': action, 'version': complaint.updated_at.isoformat(), **values})
        self.assertEqual(post('assign', department=department.pk, due_at='2026-11-06T12:30').status_code, 302)
        assignment = ComplaintAssignment.objects.get(complaint=complaint)
        self.assertEqual((timezone.localtime(assignment.due_at).hour, timezone.localtime(assignment.due_at).minute), (12, 30))
        self.assertEqual(post('submit', internal_note='تم الإصلاح').status_code, 302)
        self.assertTrue(AssignmentAction.objects.filter(assignment=assignment).exists())
        self.assertEqual(post('approved', internal_note='تمت مراجعة الأدلة', public_message='اكتمل إصلاح الإنارة', confirm='on').status_code, 302)
        complaint.refresh_from_db()
        assignment.refresh_from_db()
        self.assertEqual(complaint.status, 'completed')
        self.assertEqual(assignment.status, 'approved')
        self.assertEqual(complaint.reviews.get().reviewer_id, user.pk)
        self.assertTrue(ComplaintPublication.objects.get(complaint=complaint).approved)

    def test_legacy_assignment_links_open_the_matching_complaint(self):
        from .models import ComplaintAssignment
        admin_user = User.objects.create_superuser('legacy-assignment-admin', password='test-password')
        complaint = Complaint.objects.create(
            pk=41, reference='YBC-ADMIN-41', title='إنارة', description='تفاصيل',
        )
        department = Department.objects.create(name='الإنارة')
        assignment = ComplaintAssignment.objects.create(pk=7, complaint=complaint, department=department)
        self.client.force_login(admin_user)
        for suffix in ('change/', 'history/', 'delete/', ''):
            with self.subTest(suffix=suffix):
                self.assertRedirects(
                    self.client.get(f'/admin/complaints/complaintassignment/{assignment.pk}/{suffix}'),
                    f'/admin/complaints/complaint/{complaint.pk}/change/',
                    fetch_redirect_response=False,
                )
        for suffix in ('', 'add/'):
            self.assertRedirects(
                self.client.get('/admin/complaints/complaintassignment/' + suffix),
                '/admin/complaints/complaint/', fetch_redirect_response=False,
            )
        self.assertTrue(ComplaintAssignment.objects.filter(pk=assignment.pk).exists())

    def test_legacy_assignment_redirects_require_admin_login(self):
        response = self.client.get('/admin/complaints/complaintassignment/7/change/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/admin/login/?next='))

    def test_complaint_history_has_readable_arabic_stages(self):
        admin_user = User.objects.create_superuser('history-admin', password='test-password')
        complaint = Complaint.objects.create(reference='YBC-HISTORY-1', title='إنارة', description='تفاصيل')
        ComplaintStatusHistory.objects.create(
            complaint=complaint, status='completed', public_message='تم التحقق من الإصلاح', actor=admin_user,
        )
        self.client.force_login(admin_user)
        response = self.client.get(f'/admin/complaints/complaint/{complaint.pk}/change/')
        self.assertContains(response, 'dashboard-history-table')
        self.assertContains(response, 'أغلقت بعد الاعتماد')
        self.assertContains(response, 'تم التحقق من الإصلاح')
        self.assertNotContains(response, 'ComplaintStatusHistory object')


class StaffReportTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group
        self.user = User.objects.create_user('reporter', is_staff=True)
        self.user.groups.add(Group.objects.create(name='Complaint Reviewer'))
        self.client.force_login(self.user)

    def test_empty_report_is_html(self):
        response = self.client.get('/staff/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'staff/reports.html')
        self.assertContains(response, 'لا توجد شكاوى مسجلة بعد')
        self.assertEqual(response.context['completion_rate'], 0)

    def test_counts_and_overdue_department_work(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import ComplaintAssignment, InternalNotification
        department = Department.objects.create(name='الطرق')
        complaint = Complaint.objects.create(reference='REPORT-1', title='إنارة', description='تفاصيل', tracking_hash='unused')
        Complaint.objects.create(reference='REPORT-2', title='منجزة', description='تفاصيل', tracking_hash='unused', status='completed')
        for status in ['assigned', 'approved', 'cancelled']:
            ComplaintAssignment.objects.create(complaint=complaint, department=department, status=status, due_at=timezone.now() - timedelta(days=1))
        InternalNotification.objects.create(user=self.user, message='تنبيه')
        response = self.client.get('/staff/reports/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_complaints'], 2)
        self.assertEqual(response.context['open_complaints'], 1)
        self.assertEqual(response.context['completion_rate'], 50)
        self.assertEqual(response.context['overdue_count'], 1)
        self.assertEqual(response.context['total_assignments'], 3)
        self.assertEqual(response.context['unread_notifications'], 1)
        row = response.context['departments'].get()
        self.assertEqual((row.total, row.approved, row.overdue), (3, 1, 1))
        self.assertContains(response, 'REPORT-1')
        self.assertContains(response, 'غير مسندة لموظف')

    def test_nonstaff_cannot_read_report(self):
        self.user.is_staff = False
        self.user.save()
        self.assertEqual(self.client.get('/staff/reports/').status_code, 403)


class PublicComplaintPagesTests(TestCase):
    def test_tracking_normalizes_reference_and_hides_private_details(self):
        submitted = self.client.post('/api/complaints/', {'title': 'إنارة الحي', 'description': 'تعطل الإنارة'}).json()
        arabic_reference = submitted['reference'].lower().translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))
        response = self.client.get('/complaints/track/', {
            'reference': '  ' + arabic_reference + '  ',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/base.html')
        self.assertNotContains(response, 'إنارة الحي')
        self.assertContains(response, 'تم الاستلام')
        self.assertEqual(response['Cache-Control'], 'no-store')
        invalid = self.client.get('/complaints/track/', {'reference': 'YBC-0000-000000'})
        self.assertContains(invalid, 'لم نعثر على شكوى بهذا الرقم')
        self.assertNotContains(invalid, 'إنارة الحي')
        self.assertIsNone(invalid.context.get('tracking_result'))

    def test_home_tracking_and_submission_share_website_layout(self):
        for path in ['/', '/complaints/track/', '/complaints/submit/']:
            response = self.client.get(path)
            self.assertTemplateUsed(response, 'website/base.html')
            self.assertContains(response, 'core/public.')
        home = self.client.get('/')
        self.assertContains(home, 'name="reference"')
        self.assertNotContains(home, 'name="tracking_code"')
        self.assertContains(home, 'action="/#tracking"')
        self.assertNotContains(self.client.get('/complaints/submit/'), '<select')

    def test_home_tracking_displays_current_status(self):
        complaint = Complaint.objects.create(reference='YBC-2026-900003', title='إنارة', description='تفاصيل', tracking_hash='unused', status='assigned')
        ComplaintStatusHistory.objects.create(complaint=complaint, status='assigned', public_message='تمت الإحالة إلى القسم المختص')
        response = self.client.get('/', {'reference': complaint.reference})
        self.assertContains(response, 'تمت الإحالة')
        self.assertContains(response, complaint.reference)

    def test_existing_complaint_tracks_by_reference_without_exposing_details(self):
        complaint = Complaint.objects.create(
            reference='YBC-2026-605631', tracking_hash='legacy-stored-hash',
            title='Private title', description='Private description',
            name='Private name', phone='Private phone', email='private@example.com',
        )
        response = self.client.post('/api/complaints/track/', {'reference': complaint.reference})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {'reference', 'status', 'status_code', 'submitted_at', 'timeline'})
        self.assertNotContains(response, 'Private')
        self.assertNotContains(response, 'private@example.com')


@override_settings(
    DEBUG=False,
    ALLOWED_HOSTS=['council.example.org'],
    CSRF_COOKIE_SECURE=True,
    SESSION_COOKIE_SECURE=True,
    SECURE_SSL_REDIRECT=True,
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
)
class TrackingCsrfTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.complaint = Complaint.objects.create(
            reference='YBC-2026-605631', title='Private title', description='Private description',
            name='Private name', email='private@example.com',
        )
        self.proxy_headers = {'HTTP_HOST': 'council.example.org', 'HTTP_X_FORWARDED_PROTO': 'https'}

    def test_public_forms_use_get_and_tracking_works_without_cookies(self):
        for path in ['/', '/complaints/track/']:
            response = self.client.get(path, **self.proxy_headers)
            self.assertContains(response, 'method="get" action="/#tracking"')
            self.assertNotContains(response, 'name="csrfmiddlewaretoken"')
        self.client.cookies.clear()
        response = self.client.get('/complaints/track/', {'reference': self.complaint.reference}, **self.proxy_headers)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تم الاستلام')
        self.assertNotContains(response, 'Private')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertNotIn('csrftoken', self.client.cookies)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, 'submitted')
        self.assertEqual(self.complaint.status_history.count(), 0)

    def test_api_lookup_works_without_csrf_and_invalid_reference_has_clear_error(self):
        response = self.client.get('/api/complaints/track/', {'reference': self.complaint.reference}, **self.proxy_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reference'], self.complaint.reference)
        self.assertNotIn('title', response.json())
        invalid = self.client.get('/complaints/track/', {'reference': 'YBC-0000-000000'}, **self.proxy_headers)
        self.assertContains(invalid, 'لم نعثر على شكوى بهذا الرقم')
        self.assertEqual(self.client.get('/api/complaints/track/', {'reference': 'missing'}, **self.proxy_headers).status_code, 404)

    def test_csrf_is_still_required_for_writes_and_legacy_tracking_posts(self):
        self.assertEqual(self.client.post('/api/complaints/', {'title': 'test', 'description': 'test'}, **self.proxy_headers).status_code, 403)
        self.assertEqual(self.client.post('/complaints/track/', {'reference': self.complaint.reference}, **self.proxy_headers).status_code, 403)
        self.client.get('/complaints/submit/', **self.proxy_headers)
        token = self.client.cookies['csrftoken'].value
        response = self.client.post('/complaints/track/', {
            'reference': self.complaint.reference, 'csrfmiddlewaretoken': token,
        }, HTTP_ORIGIN='https://council.example.org', **self.proxy_headers)
        self.assertContains(response, 'تم الاستلام')

    def test_lookup_result_and_errors_stay_on_homepage(self):
        from .models import ComplaintStatusHistory
        ComplaintStatusHistory.objects.create(complaint=self.complaint, status='submitted', public_message='تم استلام الشكوى للمتابعة')
        response = self.client.get('/', {'reference': self.complaint.reference}, **self.proxy_headers)
        self.assertTemplateUsed(response, 'website/home.html')
        self.assertContains(response, 'خدمات بلدية أقرب إلى الناس')
        self.assertContains(response, 'تحديثات الشكوى')
        self.assertContains(response, 'تم استلام الشكوى للمتابعة')
        self.assertContains(response, 'value="YBC-2026-605631"')
        self.assertNotContains(response, 'Private')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertLess(response.content.index(b'id="tracking"'), response.content.index('تحديثات الشكوى'.encode()))
        invalid = self.client.get('/', {'reference': 'YBC-0000-000000'}, **self.proxy_headers)
        self.assertTemplateUsed(invalid, 'website/home.html')
        self.assertContains(invalid, 'لم نعثر على شكوى بهذا الرقم')
        self.assertContains(invalid, 'خدمات بلدية أقرب إلى الناس')
        self.assertNotContains(invalid, 'تحديثات الشكوى')
