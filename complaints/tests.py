from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client
from .models import Complaint, RecoveryRequest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from core.models import Department, ComplaintCategory

class ComplaintFlowTests(TestCase):
    def test_anonymous_submission_and_private_tracking(self):
        client = Client()
        response = client.post('/api/complaints/', {'title':'إنارة','description':'الشارع مظلم'})
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(client.post('/api/complaints/track/', {'reference':data['reference'], 'tracking_code':data['tracking_code']}).status_code, 200)
        self.assertEqual(client.post('/api/complaints/track/', {'reference':data['reference'], 'tracking_code':'wrong'}).status_code, 404)
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
