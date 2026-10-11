from django.db import migrations, models


def create_initial_homepage(apps, schema_editor):
    HomePageContent = apps.get_model("website", "HomePageContent")
    HomePageContent.objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("website", "0005_contactmessage")]

    operations = [
        migrations.CreateModel(
            name="HomePageContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hero_title", models.CharField(default="Samen groeien met je hond.", max_length=200, verbose_name="Hoofdtitel")),
                ("hero_intro", models.TextField(default="Welkom bij Mijn Hond Als Vriend. Samen leren en genieten met je hond.", verbose_name="Welkomsttekst")),
                ("about_title", models.CharField(default="Een vereniging voor jou en je hond.", max_length=200, verbose_name="Titel over ons")),
                ("about_paragraph_1", models.TextField(default="Bij Mijn Hond Als Vriend draait het om plezier, aandacht en samen trainen.", verbose_name="Over ons — eerste alinea")),
                ("about_paragraph_2", models.TextField(default="Ontdek onze trainingen en maak kennis met onze vereniging.", verbose_name="Over ons — tweede alinea")),
                ("contact_title", models.CharField(default="Kom kennismaken!", max_length=200, verbose_name="Contacttitel")),
                ("contact_intro", models.TextField(default="Heb je vragen over onze vereniging of trainingen? Neem gerust contact met ons op.", verbose_name="Contacttekst")),
            ],
            options={"verbose_name": "Homepage inhoud", "verbose_name_plural": "Homepage inhoud"},
        ),
        migrations.RunPython(create_initial_homepage, migrations.RunPython.noop),
    ]
