from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="SitePage", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=160, verbose_name="Titel")),
            ("slug", models.SlugField(unique=True, verbose_name="URL")),
            ("introduction", models.TextField(blank=True, verbose_name="Introductie")),
            ("body", models.TextField(blank=True, help_text="Gebruik lege regels voor nieuwe alinea's.", verbose_name="Inhoud")),
            ("is_published", models.BooleanField(default=True, verbose_name="Gepubliceerd")),
            ("menu_order", models.PositiveSmallIntegerField(default=0, verbose_name="Volgorde")),
        ], options={"verbose_name": "Websitepagina", "verbose_name_plural": "Websitepagina's", "ordering": ("menu_order", "title")}),
    ]
