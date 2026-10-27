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
