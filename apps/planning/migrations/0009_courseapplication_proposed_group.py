from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0008_seasoncourseoffering')]
    operations = [migrations.AddField(model_name='courseapplication', name='proposed_group', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='proposed_applications', to='planning.traininggroup', verbose_name='Voorlopige lesgroep'))]
