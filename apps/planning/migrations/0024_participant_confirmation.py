from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('planning', '0023_application_email_verified')]
    operations = [
        migrations.AlterField(model_name='courseapplication', name='status', field=models.CharField('Status', max_length=24, choices=[('pending_confirmation','Wacht op bevestiging cursist'),('declined','Afgewezen door cursist'),('new','Nieuw'),('review','In behandeling'),('waiting','Wacht op indeling'),('processed','Verwerkt'),('rejected','Niet geplaatst / ingetrokken'),('waitlist','Wachtlijst')], default='new')),
        migrations.AddField(model_name='courseapplication', name='participant_confirmed_at', field=models.DateTimeField('Aanmelding bevestigd door cursist op', null=True, blank=True)),
        migrations.AddField(model_name='courseapplication', name='participant_declined_at', field=models.DateTimeField('Aanmelding afgewezen door cursist op', null=True, blank=True)),
    ]
