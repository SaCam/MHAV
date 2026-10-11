from django.db import migrations

PAGES = [
    ("Over onze vereniging", "over-ons", "Maak kennis met Mijn Hond Als Vriend.", 10),
    ("Doelstelling", "doelstelling", "Waar onze vereniging voor staat.", 20),
    ("Puppycursus", "puppycursus", "Samen een goede basis leggen.", 30),
    ("A-cursus", "a-cursus", "Verder werken aan de basis.", 40),
    ("B-cursus", "b-cursus", "Samen oefenen en groeien.", 50),
    ("C-cursus", "c-cursus", "Vervolgtraining voor jou en je hond.", 60),
    ("D-cursus", "d-cursus", "Samen verder trainen.", 70),
    ("Recreanten", "recreanten", "Met plezier samen bezig zijn.", 80),
    ("Behendigheid", "behendigheid", "Samen actief aan de slag.", 90),
    ("PHV / KNPV", "phv-knpv", "Informatie over de werkhondentraining.", 100),
    ("Inschrijven", "inschrijven", "Informatie over aanmelden bij MHAV.", 110),
    ("Afmelden", "afmelden", "Informatie over afmelden voor een training.", 120),
    ("Huisregels", "huisregels", "De afspraken binnen onze vereniging.", 130),
    ("Contact", "contact", "Neem contact op met MHAV.", 140),
    ("Privacy", "privacy", "Hoe MHAV omgaat met persoonsgegevens.", 150),
]


def seed(apps, schema_editor):
    SitePage = apps.get_model("website", "SitePage")
    for title, slug, intro, order in PAGES:
        SitePage.objects.get_or_create(slug=slug, defaults={
            "title": title, "introduction": intro,
            "body": "Deze pagina wordt binnenkort aangevuld door het MHAV-bestuur.",
            "menu_order": order, "is_published": True,
        })


class Migration(migrations.Migration):
    dependencies = [("website", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
