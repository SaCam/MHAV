from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Announcement(models.Model):
    # Existing model retained: do not remove existing announcements.
    title = models.CharField(max_length=160)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title


class NewsPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Concept"
        REVIEW = "review", "Ter beoordeling"
        PUBLISHED = "published", "Gepubliceerd"

    title = models.CharField("Titel", max_length=180)
    slug = models.SlugField("URL-naam", max_length=210, unique=True, blank=True)
    summary = models.CharField("Samenvatting", max_length=320)
    body = models.TextField("Artikel")
    image = models.ImageField("Omslagfoto", upload_to="news/%Y/%m/", blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="mhav_news_posts")
    status = models.CharField("Status", max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    published_at = models.DateTimeField("Publicatiedatum", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Nieuwsbericht"
        verbose_name_plural = "Nieuwsberichten"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title, allow_unicode=False)[:185] or "nieuws"
            candidate = base
            index = 2
            while type(self).objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                suffix = f"-{index}"
                candidate = base[:210 - len(suffix)] + suffix
                index += 1
            self.slug = candidate
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @classmethod
    def public(cls):
        return cls.objects.filter(status=cls.Status.PUBLISHED, published_at__lte=timezone.now())

    def __str__(self):
        return self.title
