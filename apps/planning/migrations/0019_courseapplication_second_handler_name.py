from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('planning', '0018_registration_submission_source')]
    operations = [migrations.AddField(model_name='courseapplication', name='second_handler_name', field=models.CharField(blank=True, max_length=200, verbose_name='Tweede geleider (naam)'))]
