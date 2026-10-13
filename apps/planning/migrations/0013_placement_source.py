from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('planning', '0012_confirmation_email_status')]
    operations = [migrations.AddField(model_name='courseapplication', name='placement_source', field=models.CharField(choices=[('legacy', 'Onbekend (bestaand)'), ('manual', 'Handmatig'), ('automatic', 'Automatisch')], default='legacy', max_length=12, verbose_name='Herkomst conceptplaatsing'))]
