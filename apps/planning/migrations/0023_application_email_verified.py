from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('planning', '0022_alternative_season_proposal')]
    operations = [migrations.AddField(model_name='courseapplication', name='email_verified_at', field=models.DateTimeField('E-mailadres bevestigd op', null=True, blank=True))]
