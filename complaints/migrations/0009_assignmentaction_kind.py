from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('complaints', '0008_reconcile_workflow')]

    operations = [
        migrations.AddField(
            model_name='assignmentaction',
            name='kind',
            field=models.CharField(
                choices=[('submission', 'إجراء مرسل للمراجعة'), ('note', 'ملاحظة داخلية')],
                default='submission', max_length=12, verbose_name='نوع السجل',
            ),
        ),
    ]
