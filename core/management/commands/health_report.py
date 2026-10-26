from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'Check application dependencies for cron/monitoring.'
    def handle(self, *args, **options):
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        self.stdout.write(self.style.SUCCESS('database: ok; media: ok; application: ok'))
