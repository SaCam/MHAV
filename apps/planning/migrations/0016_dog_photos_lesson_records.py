from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('planning', '0015_courseapplication_outcome')]
    operations = [
        migrations.AddField(model_name='dog', name='photo', field=models.ImageField(blank=True, null=True, upload_to='dogs/%Y/%m/', verbose_name='Foto hond')),
        migrations.AddField(model_name='courseapplication', name='dog_profile', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_applications', to='planning.dog')),
        migrations.CreateModel(name='LessonRecord', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('lesson_date', models.DateField(verbose_name='Lesdatum')), ('attendance', models.CharField(choices=[('unknown','Nog niet ingevuld'),('present','Aanwezig'),('absent','Afwezig'),('excused','Afgemeld')], default='unknown', max_length=10, verbose_name='Aanwezigheid')), ('rating', models.CharField(blank=True, choices=[('','Niet beoordeeld'),('attention','Aandacht nodig'),('good','Goed'),('excellent','Uitstekend')], default='', max_length=12, verbose_name='Beoordeling')), ('notes', models.TextField(blank=True, verbose_name='Lesnotities')), ('updated_at', models.DateTimeField(auto_now=True)), ('enrollment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_records', to='planning.enrollment'))], options={'ordering': ('lesson_date','enrollment_id')}),
        migrations.AddConstraint(model_name='lessonrecord', constraint=models.UniqueConstraint(fields=('enrollment','lesson_date'), name='unique_mhav_lesson_record')),
    ]
