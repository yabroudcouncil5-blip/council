import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Create or update the initial admin from temporary environment variables.'
    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_ADMIN_USERNAME')
        password = os.environ.get('DJANGO_ADMIN_PASSWORD')
        email = os.environ.get('DJANGO_ADMIN_EMAIL', '')
        if not username and not password:
            self.stdout.write('Admin bootstrap skipped (credentials not configured).')
            return
        if not username or not password:
            raise CommandError('Set both DJANGO_ADMIN_USERNAME and DJANGO_ADMIN_PASSWORD.')
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(('Created' if created else 'Updated') + f' admin user: {username}'))
