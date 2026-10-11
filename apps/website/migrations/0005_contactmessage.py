from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("website", "0004_website_images_instructors")]
    operations = [
        migrations.CreateModel(
            name="ContactMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Naam")),
                ("email", models.EmailField(max_length=254, verbose_name="E-mailadres")),
                ("subject", models.CharField(max_length=160, verbose_name="Onderwerp")),
                ("message", models.TextField(verbose_name="Bericht")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Ontvangen")),
                ("handled", models.BooleanField(default=False, verbose_name="Afgehandeld")),
            ],
            options={"verbose_name": "Contactbericht", "verbose_name_plural": "Contactberichten", "ordering": ("-created_at",)},
        ),
    ]
