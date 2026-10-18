from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('planning', '0020_application_identity_verification')]

    operations = [
        migrations.AddField(
            model_name='courseapplication', name='start_preference',
            field=models.CharField(choices=[('earliest', 'Zo snel mogelijk'), ('specific', 'Ik heb een voorkeur voor een bepaalde cursusperiode'), ('flexible', 'Het maakt mij niet uit wanneer ik begin')], default='flexible', max_length=12, verbose_name='Gewenste start'),
        ),
        migrations.AddField(
            model_name='courseapplication', name='requested_season',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requested_applications', to='planning.season', verbose_name='Oorspronkelijk gevraagd seizoen'),
        ),
        migrations.RunSQL(
            sql="UPDATE planning_courseapplication SET requested_season_id = season_id, start_preference = 'specific' WHERE season_id IS NOT NULL",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
