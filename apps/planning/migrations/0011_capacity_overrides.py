from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0010_traininggroup_planning_lock'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='courseapplication', name='capacity_override_by', field=models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, related_name='mhav_draft_capacity_exceptions')),
        migrations.AddField(model_name='courseapplication', name='capacity_override_at', field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name='enrollment', name='capacity_override_by', field=models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, related_name='mhav_capacity_exceptions')),
        migrations.AddField(model_name='enrollment', name='capacity_override_at', field=models.DateTimeField(null=True, blank=True)),
    ]
