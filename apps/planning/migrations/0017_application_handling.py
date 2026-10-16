from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0016_dog_photos_lesson_records'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='courseapplication', name='closure_reason', field=models.CharField('Afhandelreden', max_length=24, blank=True, choices=[('capacity', 'Geen beschikbare plaats'), ('availability', 'Geen passend lesmoment'), ('withdrawn', 'Ingetrokken door aanvrager'), ('other', 'Overige reden')])),
        migrations.AddField(model_name='courseapplication', name='closure_note', field=models.TextField('Toelichting afhandeling', blank=True)),
        migrations.AddField(model_name='courseapplication', name='handled_at', field=models.DateTimeField('Afgehandeld op', null=True, blank=True)),
        migrations.AddField(model_name='courseapplication', name='handled_by', field=models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, related_name='handled_mhav_applications')),
        migrations.AlterField(model_name='courseapplication', name='status', field=models.CharField('Status', max_length=12, default='new', choices=[('new', 'Nieuw'), ('review', 'In behandeling'), ('waiting', 'Wacht op indeling'), ('processed', 'Verwerkt'), ('rejected', 'Niet geplaatst / ingetrokken'), ('waitlist', 'Wachtlijst')])),
    ]
