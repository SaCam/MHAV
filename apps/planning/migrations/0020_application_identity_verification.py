from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0019_courseapplication_second_handler_name'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='courseapplication', name='identity_verified_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_course_applications', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='courseapplication', name='identity_verified_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='courseapplication', name='identity_verification_method', field=models.CharField(blank=True, max_length=32, choices=[('in_person','Persoonlijk gecontroleerd'),('video_call','Videogesprek'),('authenticated_contact','Gecontroleerd contactkanaal')])),
        migrations.AddField(model_name='courseapplication', name='identity_verification_reference', field=models.CharField(blank=True, max_length=500)),
    ]
