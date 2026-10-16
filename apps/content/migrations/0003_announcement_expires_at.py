from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('content', '0002_newspost')]
    operations = [migrations.AddField(model_name='announcement', name='expires_at', field=models.DateTimeField(blank=True, help_text='Laat leeg voor geen einddatum.', null=True, verbose_name='Zichtbaar tot'))]
