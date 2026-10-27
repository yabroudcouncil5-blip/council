from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client, override_settings
from .models import Complaint, RecoveryRequest
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

    def test_multi_department_assignment_and_closure_guard(self):
        user=User.objects.create_user('reviewer', password='pass'); user.is_staff=True; user.save(); d1=Department.objects.create(name='طرق'); d2=Department.objects.create(name='إنارة'); client=Client(); client.force_login(user)
        response=client.post('/api/complaints/', {'title':'مشكلة مشتركة','description':'تفاصيل'}); complaint=Complaint.objects.get(reference=response.json()['reference'])
        a1=client.post('/staff/assign/', {'complaint_id':complaint.id,'department_id':d1.id}).json()['assignment_id']; a2=client.post('/staff/assign/', {'complaint_id':complaint.id,'department_id':d2.id}).json()['assignment_id']
        self.assertNotEqual(a1,a2); self.assertEqual(client.post('/staff/final-review/', {'complaint_id':complaint.id,'assignment_id':a1,'decision':'approved'}).status_code, 200); self.assertEqual(client.post('/staff/final-review/', {'complaint_id':complaint.id,'decision':'closed'}).status_code, 409)

    def test_public_resolutions_only_include_approved_completed_items(self):
        user=User.objects.create_user('reviewer2', password='pass'); user.is_staff=True; user.save(); client=Client(); client.force_login(user); d=Department.objects.create(name='خدمات')
        response=client.post('/api/complaints/', {'title':'خدمة','description':'تفاصيل'}); complaint=Complaint.objects.get(reference=response.json()['reference']); a=client.post('/staff/assign/', {'complaint_id':complaint.id,'department_id':d.id}).json()['assignment_id']; client.post('/staff/final-review/', {'complaint_id':complaint.id,'assignment_id':a,'decision':'approved'}); client.post('/staff/final-review/', {'complaint_id':complaint.id,'decision':'closed'}); complaint.refresh_from_db(); client.post('/staff/publish/', {'complaint_id':complaint.id,'summary':'تم الحل','visibility':'public'}); self.assertEqual(client.get('/api/public/resolutions/').status_code, 200)

    def test_staff_report_is_protected(self):
        self.assertEqual(Client().get('/staff/reports/').status_code, 302)

    def test_staff_dashboard_requires_staff(self):
        user=User.objects.create_user('resident',password='pass'); client=Client(); client.force_login(user); self.assertEqual(client.get('/staff/dashboard/').status_code, 403)

class StaffReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reporter', is_staff=True)
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
        self.assertContains(home, 'action="/complaints/track/"')
        self.assertNotContains(self.client.get('/complaints/submit/'), '<select')

    def test_existing_complaint_tracks_by_reference_without_exposing_details(self):
        complaint = Complaint.objects.create(
            reference='YBC-2026-605631', tracking_hash='legacy-stored-hash',
            title='Private title', description='Private description',
            name='Private name', phone='Private phone', email='private@example.com',
        )
        response = self.client.post('/api/complaints/track/', {'reference': complaint.reference})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {'reference', 'status', 'submitted_at', 'timeline'})
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
            self.assertContains(response, 'method="get" action="/complaints/track/"')
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
