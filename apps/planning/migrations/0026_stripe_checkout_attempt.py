from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0025_registration_payment')]
    operations = [migrations.CreateModel(name='StripeCheckoutAttempt', fields=[
        ('id', models.BigAutoField(primary_key=True, serialize=False)),
        ('session_id', models.CharField(max_length=255, unique=True)),
        ('payment_intent_id', models.CharField(max_length=255, blank=True)),
        ('amount_cents', models.PositiveIntegerField()),
        ('currency', models.CharField(default='eur', max_length=3)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('completed_at', models.DateTimeField(blank=True, null=True)),
        ('payment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stripe_attempts', to='planning.registrationpayment')),
    ], options={'ordering': ('-created_at',)})]
