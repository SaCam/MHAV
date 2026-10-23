from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('planning', '0027_payment_deadlines')]
    operations = [
        migrations.AddField(model_name='seasoncourseoffering', name='course_price', field=models.DecimalField(blank=True, null=True, max_digits=9, decimal_places=2, verbose_name='Cursusprijs')),
        migrations.AddField(model_name='seasoncourseoffering', name='payment_term_days', field=models.PositiveSmallIntegerField(default=14, verbose_name='Betaaltermijn (dagen)')),
        migrations.AddField(model_name='seasoncourseoffering', name='grace_period_days', field=models.PositiveSmallIntegerField(default=3, verbose_name='Respijtperiode (dagen)')),
    ]
