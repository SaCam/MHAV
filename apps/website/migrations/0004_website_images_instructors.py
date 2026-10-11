from django.db import migrations, models


def seed_images(apps, schema_editor):
    Image = apps.get_model("website", "WebsiteImage")
    for key, title in [
        ("home-hero", "Homepage — grote foto"),
        ("home-about", "Homepage — over ons"),
        ("phv-hero", "PHV — omslagfoto"),
        ("courses-hero", "Cursussen — omslagfoto"),
        ("general-hero", "Algemeen — omslagfoto"),
        ("contact-hero", "Contact — omslagfoto"),
    ]:
        Image.objects.get_or_create(key=key, defaults={"title": title})


class Migration(migrations.Migration):
    dependencies = [("website", "0003_enrich_page_content")]
    operations = [
        migrations.CreateModel(
            name="WebsiteImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(unique=True, verbose_name="Afbeeldingscode")),
                ("title", models.CharField(max_length=120, verbose_name="Naam")),
                ("image", models.ImageField(blank=True, null=True, upload_to="website/", verbose_name="Foto")),
                ("alt_text", models.CharField(blank=True, max_length=200, verbose_name="Alternatieve tekst")),
            ],
            options={"verbose_name": "Websitefoto", "verbose_name_plural": "Websitefoto's", "ordering": ("title",)},
        ),
        migrations.CreateModel(
            name="Instructor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Naam")),
                ("role", models.CharField(blank=True, max_length=160, verbose_name="Rol / specialisatie")),
                ("biography", models.TextField(blank=True, verbose_name="Introductie")),
                ("photo", models.ImageField(blank=True, null=True, upload_to="instructors/", verbose_name="Portretfoto")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="Volgorde")),
                ("is_visible", models.BooleanField(default=True, verbose_name="Zichtbaar op website")),
            ],
            options={"verbose_name": "Instructeur", "verbose_name_plural": "Instructeurs", "ordering": ("order", "name")},
        ),
        migrations.RunPython(seed_images, migrations.RunPython.noop),
    ]
