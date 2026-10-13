from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('planning', '0011_capacity_overrides')]
    operations = [
        migrations.AddField(model_name='courseapplication', name='confirmation_email_status', field=models.CharField(max_length=12, default='not_sent', verbose_name='Bevestigingsmail', choices=[('not_sent','Nog niet verzonden'),('sent','Verzonden'),('failed','Verzenden mislukt')])),
        migrations.AddField(model_name='courseapplication', name='confirmation_email_sent_at', field=models.DateTimeField(null=True, blank=True, verbose_name='Bevestigingsmail verzonden op')),
    ]
