from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0009_courseapplication_proposed_group'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='traininggroup', name='planning_locked_at', field=models.DateTimeField(blank=True, null=True, verbose_name='Conceptplanning goedgekeurd op')),
        migrations.AddField(model_name='traininggroup', name='planning_locked_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_mhav_group_plans', to=settings.AUTH_USER_MODEL)),
    ]
