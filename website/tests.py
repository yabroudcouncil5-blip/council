import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from core.models import CouncilSettings


class CouncilLogoTests(TestCase):
    def test_logo_upload_display_and_removal(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            user = get_user_model().objects.create_superuser('admin', 'admin@example.com', 'test-password')
            self.client.force_login(user)
            council = CouncilSettings.objects.create(name='بلدية يبرود')
            url = f'/admin/core/councilsettings/{council.pk}/change/'
            image = BytesIO()
            Image.new('RGB', (32, 32), 'green').save(image, format='PNG')
            response = self.client.post(url, {
                'name': council.name,
                'logo': SimpleUploadedFile('logo.png', image.getvalue(), content_type='image/png'),
                '_save': 'Save',
            })
            self.assertEqual(response.status_code, 302)
            council.refresh_from_db()
            self.assertTrue(council.logo.storage.exists(council.logo.name))
            self.assertContains(self.client.get('/'), council.logo.url)
            self.assertEqual(self.client.post(url, {'name': council.name, 'logo-clear': 'on', '_save': 'Save'}).status_code, 302)
            self.assertContains(self.client.get('/'), '<span class="mark">ي</span>', html=True)

    def test_invalid_image_is_rejected(self):
        from django.forms import modelform_factory
        form = modelform_factory(CouncilSettings, fields=['name', 'logo'])(
            data={'name': 'Council'},
            files={'logo': SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('logo', form.errors)

    def test_no_council_uses_default_mark(self):
        self.assertContains(self.client.get('/'), '<span class="mark">ي</span>', html=True)

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_public_logo_is_served_in_production_without_exposing_attachments(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            image = BytesIO()
            Image.new('RGB', (16, 16), 'green').save(image, format='PNG')
            council = CouncilSettings.objects.create(name='Council', logo=SimpleUploadedFile('test.png', image.getvalue()))
            response = self.client.get(council.logo.url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertEqual(b''.join(response.streaming_content), image.getvalue())
            response.close()
            self.assertEqual(self.client.get('/media/council/logos/unknown.png').status_code, 404)
            self.assertEqual(self.client.get('/media/complaints/private.png').status_code, 404)
            council.logo.storage.delete(council.logo.name)
            self.assertEqual(self.client.get(council.logo.url).status_code, 404)


class PageEditorTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('editor', 'editor@example.com', 'test-password')

    def test_editor_saves_and_renders_formatting_and_strips_active_html(self):
        from website.models import Page
        self.client.force_login(self.admin)
        response = self.client.get('/admin/website/page/add/')
        self.assertContains(response, 'class="council-editor"')
        self.assertContains(response, '/quill/quill.')
        self.assertContains(response, 'حجم الخط')
        response = self.client.post('/admin/website/page/add/', {
            'title': 'عن المجلس', 'slug': 'about', 'published': 'on', '_save': 'Save',
            'body': '<h2>مرحبا</h2><p class="ql-align-center" style="font-size:32px;position:fixed">نص <strong>عريض</strong></p><script>alert(1)</script><img src="javascript:alert(1)" onerror="alert(2)">',
        })
        self.assertEqual(response.status_code, 302)
        body = Page.objects.get(slug='about').body
        self.assertNotIn('<script', body)
        self.assertNotIn('onerror', body)
        self.assertNotIn('javascript:', body)
        self.assertNotIn('position', body)
        self.client.logout()
        response = self.client.get('/about/')
        self.assertContains(response, '<h2>مرحبا</h2>', html=True)
        self.assertContains(response, '<strong>عريض</strong>', html=True)
        self.assertContains(response, 'font-size:32px')
        self.assertContains(response, 'ql-align-center')

    def test_existing_text_and_unpublished_custom_pages(self):
        from website.models import Page
        Page.objects.create(slug='about', title='عن البلدية', body='السطر الأول\nالسطر الثاني\n\nفقرة جديدة', published=True)
        self.assertContains(self.client.get('/about/'), 'السطر الأول<br>السطر الثاني', html=False)
        page = Page.objects.create(slug='projects', title='المشاريع', body='<h2>مشاريع</h2>', published=False)
        self.assertEqual(self.client.get(page.get_absolute_url()).status_code, 404)
        page.published = True
        page.save()
        self.assertContains(self.client.get(page.get_absolute_url()), '<h2>مشاريع</h2>', html=True)

    def test_image_upload_permissions_validation_and_production_serving(self):
        from website.models import ContentImage
        url = '/admin/website/upload-image/'
        self.assertEqual(self.client.post(url).status_code, 302)
        limited = get_user_model().objects.create_user('limited-editor', is_staff=True)
        self.client.force_login(limited)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(url, {'image': SimpleUploadedFile('fake.png', b'bad')}).status_code, 400)
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            image = BytesIO()
            Image.new('RGB', (32, 32), 'blue').save(image, format='PNG')
            response = self.client.post(url, {'image': SimpleUploadedFile('image.png', image.getvalue(), content_type='image/png')})
            self.assertEqual(response.status_code, 201)
            public_url = response.json()['url']
            self.assertEqual(ContentImage.objects.count(), 1)
            from website.forms import PageForm
            form = PageForm(data={'title': 'صور', 'slug': 'photos', 'published': True, 'body': '<p><img src="' + public_url + '" alt="صورة المجلس"></p>'})
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            self.client.logout()
            self.assertContains(self.client.get('/pages/photos/'), public_url)
            with override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False):
                response = self.client.get(public_url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'image/webp')
                self.assertTrue(b''.join(response.streaming_content))
                response.close()
                self.assertEqual(self.client.get('/website-images/missing.webp').status_code, 404)

    def test_unsafe_markup_is_filtered_when_rendering_legacy_database_content(self):
        from website.models import NewsArticle
        NewsArticle.objects.create(title='خبر', published=True, body='<p>خبر <strong>هام</strong></p><script>alert(1)</script>')
        response = self.client.get('/news/')
        self.assertContains(response, '<strong>هام</strong>', html=True)
        self.assertNotContains(response, '<script>alert(1)</script>')
