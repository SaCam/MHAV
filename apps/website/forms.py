from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(label="Naam", max_length=120)
    email = forms.EmailField(label="E-mailadres")
    subject = forms.CharField(label="Onderwerp", max_length=160)
    message = forms.CharField(label="Bericht", widget=forms.Textarea(attrs={"rows": 6}))
    website = forms.CharField(required=False, widget=forms.HiddenInput)


from .models import HomePageContent


class HomePageEditForm(forms.ModelForm):
    class Meta:
        model = HomePageContent
        fields = ["hero_title", "hero_intro", "about_title", "about_paragraph_1", "about_paragraph_2", "contact_title", "contact_intro"]
        widgets = {
            "hero_intro": forms.Textarea(attrs={"rows": 3}),
            "about_paragraph_1": forms.Textarea(attrs={"rows": 4}),
            "about_paragraph_2": forms.Textarea(attrs={"rows": 3}),
            "contact_intro": forms.Textarea(attrs={"rows": 3}),
        }


class HomePhotoEditForm(forms.Form):
    hero_image = forms.ImageField(label="Nieuwe hoofdfoto", required=False)
    hero_alt = forms.CharField(label="Beschrijving hoofdfoto", max_length=200, required=False)
    about_image = forms.ImageField(label="Nieuwe foto Over ons", required=False)
    about_alt = forms.CharField(label="Beschrijving foto Over ons", max_length=200, required=False)
