from django.core.management.base import BaseCommand
from core.models import CouncilSettings, Department, ComplaintCategory
from website.models import Page, NewsArticle

class Command(BaseCommand):
    help = 'Seed safe local development content for Yabroud.'
    def handle(self, *args, **options):
        CouncilSettings.objects.get_or_create(name='بلدية يبرود', defaults={'description':'خدمة المدينة وأهلها بشفافية ومسؤولية.','phone':'011-0000000','email':'info@yabroud.gov.sy'})
        for name in ['النظافة والبيئة','الطرق والإنارة','المياه والصرف الصحي','الخدمات الإدارية']:
            Department.objects.get_or_create(name=name)
        for name, days in [('النظافة والبيئة',5),('الطرق والإنارة',7),('المياه والصرف الصحي',3),('الخدمات الإدارية',3)]: ComplaintCategory.objects.get_or_create(name=name, defaults={'default_days':days})
        Page.objects.get_or_create(slug='about', defaults={'title':'عن بلدية يبرود','body':'تعمل بلدية يبرود على تقديم الخدمات البلدية وتحسين المدينة.','published':True})
        NewsArticle.objects.get_or_create(title='مرحباً بكم في الموقع الرسمي', defaults={'body':'سيتم نشر الأخبار والإعلانات هنا.','published':True})
        self.stdout.write(self.style.SUCCESS('Yabroud development content seeded'))
