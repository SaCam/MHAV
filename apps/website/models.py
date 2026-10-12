from django.db import models


class SitePage(models.Model):
    title = models.CharField("Titel", max_length=160)
    slug = models.SlugField("URL", unique=True)
    introduction = models.TextField("Introductie", blank=True)
    body = models.TextField("Inhoud", blank=True, help_text="Gebruik lege regels voor nieuwe alinea's.")
    is_published = models.BooleanField("Gepubliceerd", default=True)
    menu_order = models.PositiveSmallIntegerField("Volgorde", default=0)

    class Meta:
        ordering = ("menu_order", "title")
        verbose_name = "Websitepagina"
        verbose_name_plural = "Websitepagina's"

    def __str__(self):
        return self.title


class WebsiteImage(models.Model):
    """Editable image slot; templates provide a graceful placeholder when empty."""
    key = models.SlugField("Afbeeldingscode", unique=True)
    title = models.CharField("Naam", max_length=120)
    image = models.ImageField("Foto", upload_to="website/", blank=True, null=True)
    alt_text = models.CharField("Alternatieve tekst", max_length=200, blank=True)

    class Meta:
        verbose_name = "Websitefoto"
        verbose_name_plural = "Websitefoto's"
        ordering = ("title",)

    def __str__(self):
        return self.title


class Instructor(models.Model):
    user = models.OneToOneField("auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="trainer_profile", verbose_name="Gekoppeld account")
    name = models.CharField("Naam", max_length=120)
    role = models.CharField("Rol / specialisatie", max_length=160, blank=True)
    biography = models.TextField("Introductie", blank=True)
    photo = models.ImageField("Portretfoto", upload_to="instructors/", blank=True, null=True)
    order = models.PositiveSmallIntegerField("Volgorde", default=0)
    is_visible = models.BooleanField("Zichtbaar op website", default=True)

    class Meta:
        ordering = ("order", "name")
        verbose_name = "Instructeur"
        verbose_name_plural = "Instructeurs"

    def __str__(self):
        return self.name


class ContactMessage(models.Model):
    name = models.CharField("Naam", max_length=120)
    email = models.EmailField("E-mailadres")
    subject = models.CharField("Onderwerp", max_length=160)
    message = models.TextField("Bericht")
    created_at = models.DateTimeField("Ontvangen", auto_now_add=True)
    handled = models.BooleanField("Afgehandeld", default=False)

    class Meta:
        verbose_name = "Contactbericht"
        verbose_name_plural = "Contactberichten"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.subject} — {self.name}"


class HomePageContent(models.Model):
    """Editable homepage copy displayed by the public homepage template."""
    hero_title = models.CharField("Hoofdtitel", max_length=200, default="Samen groeien met je hond.")
    hero_intro = models.TextField("Welkomsttekst", default="Welkom bij Mijn Hond Als Vriend. Samen leren en genieten met je hond.")
    about_title = models.CharField("Titel over ons", max_length=200, default="Een vereniging voor jou en je hond.")
    about_paragraph_1 = models.TextField("Over ons — eerste alinea", default="Bij Mijn Hond Als Vriend draait het om plezier, aandacht en samen trainen.")
    about_paragraph_2 = models.TextField("Over ons — tweede alinea", default="Ontdek onze trainingen en maak kennis met onze vereniging.")
    contact_title = models.CharField("Contacttitel", max_length=200, default="Kom kennismaken!")
    contact_intro = models.TextField("Contacttekst", default="Heb je vragen over onze vereniging of trainingen? Neem gerust contact met ons op.")

    class Meta:
        verbose_name = "Homepage inhoud"
        verbose_name_plural = "Homepage inhoud"

    def __str__(self):
        return "Homepage"


class SectionPageContent(models.Model):
    """Editable copy for the PHV and Cursussen landing pages."""
    key = models.SlugField("Pagina", max_length=32, unique=True)
    content = models.JSONField("Pagina-inhoud", default=dict, blank=True)

    class Meta:
        verbose_name = "Sectiepagina-inhoud"
        verbose_name_plural = "Sectiepagina-inhoud"

    def __str__(self):
        return self.key
