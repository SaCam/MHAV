from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0001_initial'), ('website', '0001_initial')]
    operations = [
        migrations.AddField(model_name='traininggroup', name='course',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='training_groups', to='website.sitepage', verbose_name='Cursusaanbod')),
        migrations.AlterField(model_name='traininggroup', name='course_name',
            field=models.CharField(blank=True, max_length=160, verbose_name='Cursus / niveau (historisch)')),
    ]
