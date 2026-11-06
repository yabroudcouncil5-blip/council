from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('website', '0004_executivemember')]
    operations = [
        migrations.AlterField(model_name='page', name='title',
                              field=models.CharField(max_length=200, verbose_name='عنوان الصفحة')),
    ]
