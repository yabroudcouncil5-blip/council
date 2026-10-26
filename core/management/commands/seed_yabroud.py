from django.core.management.base import BaseCommand
from core.models import CouncilSettings, Department, ComplaintCategory
from website.models import Page, NewsArticle

class Command(BaseCommand):
    help = 'Seed safe local development content for Yabroud.'
    def handle(self, *args, **options):
        CouncilSettings.objects.get_or_create(name='بلدية يبرود', defaults={'description':'خدمة المدينة وأهلها بشفافية ومسؤولية.','phone':'011-0000000','email':'info@yabroud.gov.sy','address':'يبرود، ريف دمشق، سوريا'})
        departments = {'النظافة والبيئة':'نحافظ على نظافة الشوارع والمساحات العامة.','الطرق والإنارة':'صيانة الطرق والإنارة ومعالجة الملاحظات الخدمية.','المياه والصرف الصحي':'متابعة شبكات المياه والصرف الصحي في المدينة.','الخدمات الإدارية':'استقبال الطلبات والمعاملات والاستفسارات.'}
        for name, description in departments.items(): Department.objects.get_or_create(name=name, defaults={'description':description})
        for name, days in [('النظافة والبيئة',5),('الطرق والإنارة',7),('المياه والصرف الصحي',3),('الخدمات الإدارية',3)]: ComplaintCategory.objects.get_or_create(name=name, defaults={'default_days':days})
        Page.objects.get_or_create(slug='about', defaults={'title':'عن بلدية يبرود','body':'تعمل بلدية يبرود على تقديم الخدمات البلدية وتحسين المدينة.','published':True})
        NewsArticle.objects.get_or_create(title='مرحباً بكم في الموقع الرسمي', defaults={'body':'أطلقنا البوابة الرقمية لتسهيل الوصول إلى خدمات البلدية وتقديم الشكاوى ومتابعتها.','published':True})
        NewsArticle.objects.get_or_create(title='قنوات التواصل مع البلدية', defaults={'body':'يمكنكم استخدام نموذج الشكاوى الإلكتروني أو زيارة صفحة التواصل لإرسال ملاحظاتكم.','published':True})
        Page.objects.get_or_create(slug='services', defaults={'title':'الخدمات البلدية','body':'النظافة والبيئة، الطرق والإنارة، المياه والصرف الصحي، والخدمات الإدارية.','published':True})
        self.stdout.write(self.style.SUCCESS('Yabroud development content seeded'))
