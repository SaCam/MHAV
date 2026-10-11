from django import forms
from .models import NewsPost


class NewsSubmissionForm(forms.ModelForm):
    class Meta:
        model = NewsPost
        fields = ("title", "summary", "body")
        widgets = {"title": forms.TextInput(attrs={"placeholder": "Titel van je bericht"}),
                   "summary": forms.Textarea(attrs={"rows": 3, "placeholder": "Korte introductie"}),
                   "body": forms.Textarea(attrs={"rows": 9, "placeholder": "Schrijf je bericht"})}
