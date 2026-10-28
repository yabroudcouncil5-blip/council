from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0006_councilsettings_logo')]
    operations = [migrations.AddField(
        model_name='councilsettings', name='facebook_url',
        field=models.URLField(blank=True, verbose_name='صفحة فيسبوك المجلس'),
    )]
