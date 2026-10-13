from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0013_placement_source'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='traininggroup', name='execution_status', field=models.CharField(choices=[('planned','Gepland'),('active','Bezig'),('completed','Afgerond'),('cancelled','Geannuleerd')], default='planned', max_length=12, verbose_name='Uitvoering')),
        migrations.AddField(model_name='traininggroup', name='execution_started_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='traininggroup', name='execution_closed_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='traininggroup', name='execution_closed_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='closed_mhav_groups', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='enrollment', name='outcome', field=models.CharField(choices=[('pending','In opleiding'),('completed','Afgerond'),('stopped','Gestopt'),('not_completed','Niet afgerond')], default='pending', max_length=16, verbose_name='Eindresultaat')),
    ]
