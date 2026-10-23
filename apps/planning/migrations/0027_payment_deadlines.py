from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('planning', '0026_stripe_checkout_attempt')]
    operations = [
        migrations.AddField(model_name='registrationpayment', name='reminder_sent_at', field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name='registrationpayment', name='grace_notice_sent_at', field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name='registrationpayment', name='cancelled_at', field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name='registrationpayment', name='cancellation_reason', field=models.CharField(max_length=32, blank=True)),
    ]
