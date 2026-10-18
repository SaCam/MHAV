from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning','0024_participant_confirmation'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='RegistrationPayment', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('amount_due', models.DecimalField('Cursusbedrag', max_digits=9, decimal_places=2, null=True, blank=True)),
            ('currency', models.CharField(max_length=3, default='EUR')),
            ('reference', models.CharField('Betaalreferentie', max_length=40, unique=True)),
            ('status', models.CharField(max_length=12, choices=[('pending','Nog te betalen'),('paid','Betaald'),('waived','Vrijgesteld'),('refunded','Terugbetaald')], default='pending')),
            ('due_at', models.DateTimeField(null=True, blank=True)),
            ('paid_at', models.DateTimeField(null=True, blank=True)),
            ('method', models.CharField(max_length=12, blank=True, choices=[('bank','Bankoverschrijving'),('cash','Contant'),('other','Anders'),('online','Online')])),
            ('note', models.TextField('Toelichting betaling', blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('updated_at', models.DateTimeField(auto_now=True)),
            ('application', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='payment', to='planning.courseapplication')),
            ('paid_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mhav_payments_recorded', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name='RegistrationPaymentEvent', fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ('action', models.CharField(max_length=32)),
            ('note', models.TextField()),
            ('recorded_at', models.DateTimeField(auto_now_add=True)),
            ('old_status', models.CharField(max_length=12, blank=True)),
            ('new_status', models.CharField(max_length=12, blank=True)),
            ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ('payment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='events', to='planning.registrationpayment')),
        ], options={'ordering': ('-recorded_at','-pk')}),
    ]
