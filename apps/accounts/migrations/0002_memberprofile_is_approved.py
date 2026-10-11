from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.AddField(model_name="memberprofile", name="is_approved", field=models.BooleanField(default=False, verbose_name="Lidmaatschap bevestigd"))]
