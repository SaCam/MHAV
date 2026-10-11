from django import forms
from .section_defaults import SECTION_DEFAULTS
from .models import SitePage

LABELS = {
    "hero_first": "Titel (eerste regel)", "hero_em": "Titel (groene regel)", "hero_lead": "Introductietekst",
    "intro_title": "Koptekst", "intro_p1": "Eerste alinea", "intro_p2": "Tweede alinea",
    "steps_title": "Koptekst", "list_title": "Koptekst cursusaanbod",
    "cta_title": "Koptekst", "cta_text": "Beschrijving",
}

class SectionTextForm(forms.Form):
    def __init__(self, *args, page_key, section, content=None, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = {
            "hero": ("hero_first", "hero_em", "hero_lead"),
            "intro": ("intro_title", "intro_p1", "intro_p2"),
            "steps": ("steps_title", "step1_title", "step1_text", "step2_title", "step2_text", "step3_title", "step3_text"),
            "list": ("list_title",),
            "cta": ("cta_title", "cta_text"),
        }
        if section not in allowed or (section == "steps" and page_key != "phv") or (section == "list" and page_key != "courses"):
            raise ValueError("Invalid section")
        defaults = SECTION_DEFAULTS[page_key]
        for name in allowed[section]:
            self.fields[name] = forms.CharField(
                label=LABELS.get(name, name.replace("_", " ").capitalize()),
                max_length=160 if name.endswith("title") or name in ("hero_first", "hero_em", "list_title", "steps_title") else 2000,
                widget=forms.Textarea(attrs={"rows":3}) if name.endswith(("text", "lead", "p1", "p2")) else forms.TextInput(),
                initial=(content or {}).get(name, defaults[name]),
            )

class CourseEditForm(forms.ModelForm):
    class Meta:
        model = SitePage
        fields = ("title", "introduction", "body", "is_published", "menu_order")
        labels = {"title": "Naam van de cursus", "introduction": "Korte beschrijving", "body": "Uitgebreide informatie", "is_published": "Zichtbaar op website", "menu_order": "Volgorde"}
        widgets = {"introduction": forms.Textarea(attrs={"rows":3}), "body": forms.Textarea(attrs={"rows":7})}
