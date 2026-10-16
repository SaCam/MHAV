from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('content', '0003_announcement_expires_at')]
    operations = [migrations.AddField(model_name='announcement', name='priority', field=models.CharField(choices=[('normal', 'Normaal'), ('important', 'Belangrijk'), ('urgent', 'Urgent')], default='normal', max_length=12, verbose_name='Prioriteit'))]
