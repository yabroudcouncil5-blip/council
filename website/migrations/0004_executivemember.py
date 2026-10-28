from django.db import migrations, models


MOCK_MEMBERS = [
    ('مروان خليل', 'رئيس مجلس المدينة', 'يقود التوجه العام للمجلس، ويتابع تنفيذ أولويات المدينة، ويمثل يبرود في أعمال التنسيق والشراكة.'),
    ('ليان عيسى', 'نائب رئيس المجلس', 'تساند رئيس المجلس، وتنسق بين الملفات التنفيذية، وتتابع سير العمل المشترك بين الأقسام.'),
    ('سامر حداد', 'الأمين العام', 'ينظم المراسلات والاجتماعات والقرارات، ويضمن وصول الملفات إلى الجهات المعنية ومتابعة مخرجاتها.'),
    ('رنا منصور', 'مديرة الأقسام والخدمات', 'تنسق فرق العمل في النظافة والبيئة والطرق والتنظيم، وتحول البلاغات إلى مهام قابلة للمتابعة.'),
    ('فراس ناصر', 'منسق الخدمات الميدانية', 'يتابع حضور الفرق في الأحياء، ويرصد الاحتياجات ويتحقق من معالجة الملاحظات في مواقعها.'),
]


def seed_members(apps, schema_editor):
    ExecutiveMember = apps.get_model('website', 'ExecutiveMember')
    for order, (name, role, bio) in enumerate(MOCK_MEMBERS, 1):
        ExecutiveMember.objects.get_or_create(
            name=name, defaults={'role': role, 'bio': bio, 'display_order': order, 'active': True}
        )


class Migration(migrations.Migration):
    dependencies = [('website', '0003_contentimage')]
    operations = [
        migrations.CreateModel(
            name='ExecutiveMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=160, verbose_name='الاسم')),
                ('role', models.CharField(max_length=180, verbose_name='المسمى الوظيفي')),
                ('bio', models.TextField(verbose_name='نبذة قصيرة')),
                ('photo', models.ImageField(blank=True, upload_to='council/team/', verbose_name='صورة العضو')),
                ('display_order', models.PositiveIntegerField(default=0, verbose_name='ترتيب العرض')),
                ('active', models.BooleanField(default=True, verbose_name='ظاهر على الموقع')),
            ],
            options={'verbose_name': 'عضو الفريق التنفيذي', 'verbose_name_plural': 'الفريق التنفيذي', 'ordering': ('display_order', 'id')},
        ),
        migrations.RunPython(seed_members, migrations.RunPython.noop),
    ]
