from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('planning', '0017_application_handling'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name='courseapplication', name='submitted_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='submitted_course_applications', to=settings.AUTH_USER_MODEL, verbose_name='Ingediend door')),
        migrations.AddField(model_name='courseapplication', name='submission_source', field=models.CharField(choices=[('guest', 'Gast'), ('member', 'Mijn MHAV'), ('admin', 'Beheerder')], default='guest', max_length=12, verbose_name='Inschrijfkanaal')),
    ]
