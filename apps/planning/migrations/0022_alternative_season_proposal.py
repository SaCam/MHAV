from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0021_application_start_preference')]
    operations = [
        migrations.AddField(model_name='courseapplication', name='alternative_season', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alternative_applications', to='planning.season', verbose_name='Voorgesteld alternatief seizoen')),
        migrations.AddField(model_name='courseapplication', name='alternative_proposed_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='courseapplication', name='alternative_accepted_at', field=models.DateTimeField(blank=True, null=True)),
    ]
