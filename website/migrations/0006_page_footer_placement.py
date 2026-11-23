from django.db import migrations, models


def make_services_editable(apps, schema_editor):
    page = apps.get_model('website', 'Page')
    pages = page.objects.using(schema_editor.connection.alias)
    services, created = pages.get_or_create(
        slug='services',
        defaults={
            'title': 'الخدمات البلدية',
            'body': 'النظافة والبيئة، الطرق والإنارة، المياه والصرف الصحي، والخدمات الإدارية.',
            'published': True,
            'show_in_footer': True,
        },
    )
    if not created and services.published:
        pages.filter(pk=services.pk).update(show_in_footer=True)


class Migration(migrations.Migration):
    dependencies = [('website', '0005_alter_page_title')]

    operations = [
        migrations.AddField(
            model_name='page',
            name='show_in_footer',
            field=models.BooleanField(default=False, verbose_name='إظهار في تذييل الموقع'),
        ),
        migrations.RunPython(make_services_editable, migrations.RunPython.noop),
    ]
