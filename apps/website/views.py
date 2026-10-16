from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods
from .forms import ContactForm, HomePageEditForm, HomePhotoEditForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponseForbidden

from apps.content.models import Announcement, NewsPost
from .models import SitePage, WebsiteImage, Instructor, ContactMessage, HomePageContent, SectionPageContent


TRAINING_SLUGS = (
    "puppycursus", "a-cursus", "b-cursus", "c-cursus",
    "d-cursus", "recreanten", "behendigheid", "phv-knpv",
)
CLUB_SLUGS = ("over-ons", "doelstelling", "huisregels")
PRACTICAL_SLUGS = ("inschrijven", "afmelden", "contact", "privacy")


def images_by_key():
    return {item.key: item for item in WebsiteImage.objects.all()}


def _section_page(request, page_key, edit_section=None, form=None):
    from .section_defaults import SECTION_DEFAULTS
    from .section_forms import SectionTextForm
    from django.http import Http404
    can_text = request.user.is_authenticated and request.user.has_perm("website.change_sectionpagecontent")
    can_photo = request.user.is_authenticated and request.user.has_perm("website.change_websiteimage")
    can_courses = request.user.is_authenticated and request.user.has_perm("website.change_sitepage")
    can_manage_courses = request.user.is_authenticated and (request.user.has_perm("website.add_sitepage") or can_courses)
    entry = SectionPageContent.objects.filter(key=page_key).first()
    copy = {**SECTION_DEFAULTS[page_key], **(entry.content if entry else {})}
    edit = edit_section if edit_section in ("hero", "intro", "steps", "list", "cta", "photo") else None
    if edit == "steps" and page_key != "phv": edit = None
    if edit == "list" and page_key != "courses": edit = None
    if edit == "photo": edit = "hero"
    if edit == "hero" and not (can_text or can_photo): edit = None
    if edit not in (None, "hero") and not can_text: edit = None
    if edit and can_text and form is None:
        form = SectionTextForm(page_key=page_key, section=edit, content=copy)
    photo = WebsiteImage.objects.filter(key=page_key + "-hero").first()
    courses_qs = SitePage.objects.filter(is_published=True).filter(Q(slug__in=TRAINING_SLUGS) | Q(slug__startswith="cursus-")).exclude(slug="phv-knpv").order_by("menu_order", "title")
    published_groups = []
    if page_key == 'courses':
        from apps.planning.models import TrainingGroup, Season, SeasonCourseOffering

        open_pairs = {
            (o.season_id, o.course_id)
            for o in SeasonCourseOffering.objects.select_related('season', 'course')
            if o.accepts_applications()
        }

        published_groups = (
            TrainingGroup.objects.filter(
                season_id__in=[s for s, c in open_pairs],
                course_id__in=[c for s, c in open_pairs],
                course__is_published=True,
            )
            .exclude(execution_status='completed')
            .select_related('course', 'season', 'trainer')
            .annotate(
                placed_count=Count(
                    'enrollments',
                    filter=Q(enrollments__status='placed')
                )
            )
            .order_by('season__starts_on', 'day', 'starts_at', 'name')
        )

        published_groups = [
            g for g in published_groups
            if (g.season_id, g.course_id) in open_pairs
        ]
    return render(request, "website/" + ("phv" if page_key == "phv" else "courses") + ".html", {
        "section": page_key, "copy": copy, "photo": photo, "published_groups": published_groups,
        "feature": SitePage.objects.filter(is_published=True, slug="phv-knpv").first() if page_key == "phv" else None,
        "pages": courses_qs if page_key == "courses" else [],
        "can_text": can_text, "can_photo": can_photo, "can_edit_hero": can_text or can_photo, "can_manage_courses": can_manage_courses,
        "edit_section": edit, "section_form": form,
    })


def phv(request):
    return _section_page(request, "phv", edit_section=request.GET.get("edit"))


def courses(request):
    return _section_page(request, "courses", edit_section=request.GET.get("edit"))


@login_required
def section_page_save(request, page_key):
    from django.http import HttpResponseBadRequest
    from django.urls import reverse
    from .section_forms import SectionTextForm
    from .section_defaults import SECTION_DEFAULTS
    if page_key not in SECTION_DEFAULTS or request.method != "POST":
        return HttpResponseBadRequest("Ongeldige aanvraag")
    section = request.POST.get("section")
    target = reverse("website:phv" if page_key == "phv" else "website:courses")
    if section == "photo":
        if not request.user.has_perm("website.change_websiteimage"):
            return HttpResponseForbidden("Geen toestemming")
        from django import forms
        class PhotoForm(forms.Form):
            image = forms.ImageField(required=False)
            alt_text = forms.CharField(required=False, max_length=200)
        form = PhotoForm(request.POST, request.FILES)
        if form.is_valid():
            image, _ = WebsiteImage.objects.get_or_create(key=page_key + "-hero", defaults={"title": page_key.upper() + " hero"})
            if form.cleaned_data["image"]: image.image = form.cleaned_data["image"]
            image.alt_text = form.cleaned_data["alt_text"] or image.alt_text
            image.save()
            messages.success(request, "Foto opgeslagen")
            return redirect(target + "#hero")
        messages.error(request, "Kies een geldige afbeelding")
        return redirect(target + "?edit=photo#hero")
    if section == "hero" and request.user.has_perm("website.change_websiteimage"):
        from django import forms
        class HeroPhotoForm(forms.Form):
            image = forms.ImageField(required=False)
            alt_text = forms.CharField(required=False, max_length=200)
        photo_form = HeroPhotoForm(request.POST, request.FILES)
        if not photo_form.is_valid():
            messages.error(request, "Controleer de afbeelding.")
            return redirect(target + "?edit=hero#hero")
        if not request.user.has_perm("website.change_sectionpagecontent"):
            image, _ = WebsiteImage.objects.get_or_create(key=page_key + "-hero", defaults={"title": page_key.upper() + " hero"})
            if photo_form.cleaned_data["image"]: image.image = photo_form.cleaned_data["image"]
            if photo_form.cleaned_data["alt_text"]: image.alt_text = photo_form.cleaned_data["alt_text"]
            image.save()
            messages.success(request, "Foto opgeslagen")
            return redirect(target + "#hero")
    else:
        photo_form = None
    if not request.user.has_perm("website.change_sectionpagecontent"):
        return HttpResponseForbidden("Geen toestemming")
    try:
        entry, _ = SectionPageContent.objects.get_or_create(key=page_key)
        form = SectionTextForm(request.POST, page_key=page_key, section=section, content=entry.content)
    except ValueError:
        return HttpResponseBadRequest("Ongeldig onderdeel")
    if form.is_valid():
        entry.content = {**entry.content, **form.cleaned_data}
        entry.save(update_fields=["content"])
        if section == "hero" and photo_form:
            image, _ = WebsiteImage.objects.get_or_create(key=page_key + "-hero", defaults={"title": page_key.upper() + " hero"})
            if photo_form.cleaned_data["image"]: image.image = photo_form.cleaned_data["image"]
            if photo_form.cleaned_data["alt_text"]: image.alt_text = photo_form.cleaned_data["alt_text"]
            image.save()
        messages.success(request, "Onderdeel opgeslagen")
        return redirect(target + "#" + section)
    return _section_page(request, page_key, edit_section=section, form=form)


# Simple on-page editing for the remaining public pages.
PUBLIC_COPY = {
    "instructors": {"hero_title": "Een goed team.", "hero_em": "Voor jou en je hond.", "hero_intro": "Onze instructeurs begeleiden de trainingen en delen hun kennis en enthousiasme met de vereniging.", "list_title": "Onze instructeurs."},
    "general": {"hero_title": "Meer dan", "hero_em": "een hondenschool.", "hero_intro": "MHAV is een plek waar mensen en honden samen leren, trainen en plezier maken.", "intro_title": "Een vereniging met aandacht voor de band tussen mens en hond.", "intro_p1": "Bij MHAV staat samen trainen centraal. We geloven dat vertrouwen, duidelijke communicatie en plezier de basis vormen voor een prettige samenwerking.", "intro_p2": "Op deze pagina vind je meer over de vereniging en de praktische afspraken.", "list_title": "Alles over MHAV.", "cta_title": "Een vraag over onze vereniging?", "cta_text": "Neem contact op met MHAV voor meer informatie."},
    "contact": {"hero_title": "Contact", "hero_intro": "Wil je meer weten over MHAV of onze trainingen? We horen graag van je.", "intro_title": "Neem contact op", "form_title": "Stuur ons een bericht", "form_intro": "Vul het formulier in. Je bericht wordt opgeslagen voor de beheerders van MHAV."},
}

def _public_editor(request, key):
    from django import forms
    can_text = request.user.is_authenticated and request.user.has_perm("website.change_sectionpagecontent")
    can_photo = request.user.is_authenticated and request.user.has_perm("website.change_websiteimage")
    entry = SectionPageContent.objects.filter(key=key).first()
    copy = {**PUBLIC_COPY[key], **(entry.content if entry else {})}
    edit = request.GET.get("edit")
    sections = {"instructors": {"hero": ("hero_title", "hero_em", "hero_intro"), "list": ("list_title",)},
                "general": {"hero": ("hero_title", "hero_em", "hero_intro"), "intro": ("intro_title", "intro_p1", "intro_p2"), "list": ("list_title",), "cta": ("cta_title", "cta_text")},
                "contact": {"hero": ("hero_title", "hero_intro"), "intro": ("intro_title",), "form": ("form_title", "form_intro")}}[key]
    if edit not in sections or not can_text: edit = None
    class CopyForm(forms.Form):
        def __init__(self, *args, section, **kwargs):
            super().__init__(*args, **kwargs)
            for field in sections[section]:
                self.fields[field] = forms.CharField(label=field.replace("_", " ").capitalize(), max_length=2000,
                    initial=copy[field], widget=forms.Textarea(attrs={"rows": 3}) if field.endswith(("intro", "p1", "p2", "text")) else forms.TextInput())
    section_form = CopyForm(section=edit) if edit else None
    return {"copy": copy, "edit_section": edit, "section_form": section_form,
            "can_text": can_text, "can_photo": can_photo, "can_edit_hero": can_text or can_photo,
            "can_instructors": request.user.is_authenticated and request.user.has_perm("website.change_instructor"),
            "public_sections": sections}

@login_required
def public_page_save(request, page_key):
    from django import forms
    from django.http import HttpResponseBadRequest
    from django.urls import reverse
    if request.method != "POST" or page_key not in PUBLIC_COPY:
        return HttpResponseBadRequest("Ongeldige aanvraag")
    section = request.POST.get("section")
    allowed = {"instructors": {"hero": ("hero_title", "hero_em", "hero_intro"), "list": ("list_title",)},
               "general": {"hero": ("hero_title", "hero_em", "hero_intro"), "intro": ("intro_title", "intro_p1", "intro_p2"), "list": ("list_title",), "cta": ("cta_title", "cta_text")},
               "contact": {"hero": ("hero_title", "hero_intro"), "intro": ("intro_title",), "form": ("form_title", "form_intro")}}[page_key]
    target = reverse("website:" + page_key)
    if section not in allowed:
        return HttpResponseBadRequest("Ongeldig onderdeel")
    if not request.user.has_perm("website.change_sectionpagecontent"):
        return HttpResponseForbidden("Geen toestemming")

    values = {}
    for field in allowed[section]:
        value = request.POST.get(field, "").strip()
        if not value or len(value) > 2000:
            messages.error(request, "Vul alle tekstvelden correct in.")
            return redirect(target + "?edit=" + section + "#hero" if section == "hero" else target + "?edit=" + section)
        values[field] = value

    is_photo_section = section == "hero" and page_key in ("general", "contact")
    if is_photo_section and "image" in request.FILES and not request.user.has_perm("website.change_websiteimage"):
        return HttpResponseForbidden("Geen toestemming om foto's te bewerken")

    class PhotoUploadForm(forms.Form):
        image = forms.ImageField(required=False)

    upload_form = PhotoUploadForm(request.POST, request.FILES) if is_photo_section else None
    image = None
    if upload_form is not None:
        if not upload_form.is_valid():
            messages.error(request, "De foto kon niet worden gelezen. Gebruik een geldige JPG, PNG of WebP afbeelding.")
            return redirect(target + "?edit=hero#hero")
        image = upload_form.cleaned_data["image"]
        if image:
            if image.size > 25 * 1024 * 1024 or image.content_type not in ("image/jpeg", "image/png", "image/webp"):
                messages.error(request, "Gebruik een JPG, PNG of WebP afbeelding van maximaal 25 MB.")
                return redirect(target + "?edit=hero#hero")
            if not request.user.has_perm("website.change_websiteimage"):
                return HttpResponseForbidden("Geen toestemming om foto's te bewerken")

    try:
        with transaction.atomic():
            # Store the image first; if storage raises an error, don't claim the page was saved.
            if image:
                photo, _ = WebsiteImage.objects.get_or_create(
                    key=page_key + "-hero", defaults={"title": page_key + " hero"})
                photo.image = image
                photo.save()
            entry, _ = SectionPageContent.objects.get_or_create(key=page_key)
            entry.content = {**entry.content, **values}
            entry.save(update_fields=["content"])
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Unable to save public page %s section %s", page_key, section)
        messages.error(request, "Opslaan is mislukt. Controleer de media-opslag en probeer opnieuw.")
        return redirect(target + "?edit=" + section + "#hero" if section == "hero" else target + "?edit=" + section)
    messages.success(request, "Tekst en foto opgeslagen." if image else "Onderdeel opgeslagen.")
    return redirect(target + "#" + section)


def instructors(request):
    ctx = _public_editor(request, "instructors")
    ctx["instructors"] = Instructor.objects.filter(is_visible=True).filter(Q(user__isnull=True) | Q(user__is_active=True, user__groups__name="MHAV - Trainer")).distinct()
    return render(request, "website/instructors.html", ctx)


def general(request):
    ctx = _public_editor(request, "general")
    ctx.update({"section": "general", "title": "Algemeen", "eyebrow": "OVER ONZE VERENIGING",
        "photo": WebsiteImage.objects.filter(key="general-hero").first(),
        "pages": SitePage.objects.filter(is_published=True, slug__in=CLUB_SLUGS + ("inschrijven", "afmelden", "privacy"))})
    return render(request, "website/general.html", ctx)


@require_http_methods(["GET", "POST"])
def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not form.cleaned_data["website"]:
            ContactMessage.objects.create(name=form.cleaned_data["name"], email=form.cleaned_data["email"],
                subject=form.cleaned_data["subject"], message=form.cleaned_data["message"])
        return redirect("website:contact_thanks")
    ctx = _public_editor(request, "contact")
    ctx.update({"page": SitePage.objects.filter(slug="contact", is_published=True).first(),
        "photo": WebsiteImage.objects.filter(key="contact-hero").first(), "form": form})
    return render(request, "website/contact.html", ctx)


def contact_thanks(request):
    return render(request, "website/contact_thanks.html")


@login_required
def home_edit(request):
    """Save one homepage section; the form itself is rendered on the public homepage."""
    from django.urls import reverse
    from django.http import HttpResponseBadRequest
    section = request.POST.get("section")
    fields = {
        "hero": ("hero_title", "hero_intro"),
        "about": ("about_title", "about_paragraph_1", "about_paragraph_2"),
        "contact": ("contact_title", "contact_intro"),
    }
    if request.method != "POST" or section not in fields:
        return HttpResponseBadRequest("Ongeldige aanvraag.")
    can_text = request.user.has_perm("website.change_homepagecontent")
    can_photos = request.user.has_perm("website.change_websiteimage")
    if not can_text and not can_photos:
        return HttpResponseForbidden("Je hebt geen toestemming om deze pagina te bewerken.")

    content, _ = HomePageContent.objects.get_or_create(pk=1)
    from django.forms import modelform_factory
    SectionForm = modelform_factory(HomePageContent, fields=fields[section])
    form = SectionForm(request.POST, instance=content) if can_text else None
    image_key = {"hero": "home-hero", "about": "home-about"}.get(section)
    photo_form = None
    if can_photos and image_key:
        photo_form = HomePhotoEditForm(request.POST, request.FILES)
        # Only validate the image belonging to the section being saved.
        if section == "hero":
            photo_form.fields.pop("about_image")
            photo_form.fields.pop("about_alt")
        else:
            photo_form.fields.pop("hero_image")
            photo_form.fields.pop("hero_alt")
    if (form is None or form.is_valid()) and (photo_form is None or photo_form.is_valid()):
        with transaction.atomic():
            if form is not None:
                form.save()
            if photo_form is not None:
                photo, _ = WebsiteImage.objects.get_or_create(
                    key=image_key, defaults={"title": "Homepage — " + section}
                )
                image_field = section + "_image"
                alt_field = section + "_alt"
                new_image = photo_form.cleaned_data.get(image_field)
                if new_image:
                    photo.image = new_image
                # Don't erase the existing alt text when the field is left empty.
                new_alt = photo_form.cleaned_data.get(alt_field)
                if new_alt:
                    photo.alt_text = new_alt
                photo.save()
        messages.success(request, "Onderdeel opgeslagen.")
        return redirect(reverse("website:home") + "#" + section)
    # Re-render the real homepage with the invalid section and errors in place.
    return _render_home(request, edit_section=section, section_form=form,
                        section_photo_form=photo_form)


def _render_home(request, edit_section=None, section_form=None, section_photo_form=None):
    from django.forms import modelform_factory
    content, _ = HomePageContent.objects.get_or_create(pk=1)
    can_text = request.user.is_authenticated and request.user.has_perm("website.change_homepagecontent")
    can_photos = request.user.is_authenticated and request.user.has_perm("website.change_websiteimage")
    allowed = {"hero", "about", "contact"}
    if edit_section not in allowed or not (can_text or (can_photos and edit_section in ("hero", "about"))):
        edit_section = None
    if edit_section and can_text and section_form is None:
        fields = {
            "hero": ("hero_title", "hero_intro"),
            "about": ("about_title", "about_paragraph_1", "about_paragraph_2"),
            "contact": ("contact_title", "contact_intro"),
        }
        section_form = modelform_factory(HomePageContent, fields=fields[edit_section])(instance=content)
    if edit_section in ("hero", "about") and can_photos and section_photo_form is None:
        photo = WebsiteImage.objects.filter(key="home-" + edit_section).first()
        section_photo_form = HomePhotoEditForm(initial={
            edit_section + "_alt": photo.alt_text if photo else ""
        })
    announcements = Announcement.objects.filter(is_published=True).order_by("-published_at", "-created_at")[:3]
    news_posts = NewsPost.public().order_by("-published_at", "-created_at")[:3]
    return render(request, "website/home.html", {
        "announcements": announcements, "news_posts": news_posts,
        "home_content": content,
        "hero_photo": WebsiteImage.objects.filter(key="home-hero").first(),
        "about_photo": WebsiteImage.objects.filter(key="home-about").first(),
        "instructors": Instructor.objects.filter(is_visible=True).filter(Q(user__isnull=True) | Q(user__is_active=True, user__groups__name="MHAV - Trainer")).distinct()[:3],
        "edit_section": edit_section, "section_form": section_form,
        "section_photo_form": section_photo_form,
        "can_text": can_text, "can_photos": can_photos,
    })

def home(request):
    return _render_home(request, edit_section=request.GET.get("edit"))


def page(request, slug):
    # Preserve the old informational URL but make registration the primary route.
    if slug == 'inschrijven':
        return redirect('website:application')
    item = get_object_or_404(SitePage, slug=slug, is_published=True)
    related = SitePage.objects.filter(
        is_published=True, slug__in=TRAINING_SLUGS
    ).exclude(pk=item.pk)[:3] if slug in TRAINING_SLUGS else []
    from apps.planning.models import TrainingGroup, Season, SeasonCourseOffering
    from django.db.models import Count
    offerings = [o for o in SeasonCourseOffering.objects.filter(course=item).select_related('season') if o.approval_valid() and o.season.status != Season.Status.CLOSED]
    open_offerings = [o for o in offerings if o.accepts_applications()]
    open_season_ids = [o.season_id for o in open_offerings]
    published_groups = (TrainingGroup.objects.filter(course=item, season_id__in=open_season_ids)
     .select_related('season').annotate(placed_count=Count('enrollments', filter=Q(enrollments__status='placed')))
     .order_by('season__starts_on', 'day', 'starts_at'))
    upcoming_offering = next((o for o in sorted(offerings, key=lambda x: x.season.starts_on) if o.season.ends_on >= __import__('datetime').date.today()), None)
    upcoming_open = upcoming_offering.accepts_applications() if upcoming_offering else False
    return render(
        request, "website/page.html",
        {"page": item, "related_pages": related, "published_groups": published_groups, "upcoming_offering": upcoming_offering, "upcoming_open": upcoming_open, "is_course_page": _managed_course_queryset().filter(pk=item.pk).exists()},
    )


def page_index(request):
    published = SitePage.objects.filter(is_published=True)
    context = {
        "training_pages": published.filter(slug__in=TRAINING_SLUGS),
        "club_pages": published.filter(slug__in=CLUB_SLUGS),
        "practical_pages": published.filter(slug__in=PRACTICAL_SLUGS),
    }
    return render(request, "website/page_index.html", context)


# MHAV course catalogue: permanent course descriptions, reused by season planning.
def _can_manage_course(user, action):
    return user.is_authenticated and user.is_active and (
        user.is_superuser or user.groups.filter(name="MHAV - Administrator").exists()
        or user.has_perm("website." + action + "_sitepage")
    )

def _managed_course_queryset():
    return SitePage.objects.filter(Q(slug__in=TRAINING_SLUGS) | Q(slug__startswith="cursus-")).exclude(slug="phv-knpv")


@login_required
def course_manage(request):
    if not (_can_manage_course(request.user, "add") or _can_manage_course(request.user, "change")):
        return HttpResponseForbidden("Geen toestemming")
    if request.user.is_superuser or request.user.groups.filter(name="MHAV - Administrator").exists():
        return redirect("planning:catalogue")
    return render(request, "website/course_manage.html", {
        "courses": _managed_course_queryset().order_by("menu_order", "title"),
        "can_add": _can_manage_course(request.user, "add"),
        "can_change": _can_manage_course(request.user, "change"),
        "can_delete": _can_manage_course(request.user, "delete"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def course_form(request, pk=None):
    from .section_forms import CourseEditForm
    from django.utils.text import slugify
    import uuid
    course = get_object_or_404(_managed_course_queryset(), pk=pk) if pk is not None else None
    permission = "website.change_sitepage" if course else "website.add_sitepage"
    if not _can_manage_course(request.user, "change" if course else "add"):
        return HttpResponseForbidden("Geen toestemming")
    form = CourseEditForm(request.POST or None, instance=course)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if course is None:
            # A unique prefix keeps new courses separate from existing informational pages.
            stem = (slugify(item.title, allow_unicode=False) or "training")[:36]
            item.slug = f"cursus-{stem}-{uuid.uuid4().hex[:8]}"
        item.save()
        messages.success(request, "Cursus opgeslagen.")
        return redirect("website:course_manage")
    return render(request, "website/course_form.html", {"form": form, "course": course})


@login_required
@require_http_methods(["POST"])
def course_delete(request, pk):
    if not _can_manage_course(request.user, "delete"):
        return HttpResponseForbidden("Geen toestemming")
    course = get_object_or_404(_managed_course_queryset(), pk=pk)
    if course.training_groups.exists():
        course.is_published = False
        course.save(update_fields=['is_published'])
        messages.success(request, 'Cursus verborgen. Bestaande lesgroepen blijven gekoppeld.')
        return redirect('website:course_manage')
    # Existing seeded training pages may be referenced elsewhere; hide instead of deleting them.
    if course.slug in TRAINING_SLUGS:
        course.is_published = False
        course.save(update_fields=["is_published"])
        messages.success(request, "Bestaande cursus verborgen. Deze kan later weer gepubliceerd worden.")
    else:
        course.delete()
        messages.success(request, "Cursus verwijderd.")
    return redirect("website:course_manage")
