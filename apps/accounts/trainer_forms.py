from django import forms
from apps.website.models import Instructor

class TrainerProfileForm(forms.ModelForm):
    class Meta:
        model = Instructor
        fields = ('name', 'role', 'biography', 'photo')
        labels = {'name': 'Naam op de website', 'role': 'Functie / specialisatie', 'biography': 'Over mij', 'photo': 'Portretfoto'}
        widgets = {'biography': forms.Textarea(attrs={'rows': 6})}

class TrainerVisibilityForm(forms.ModelForm):
    class Meta:
        model = Instructor
        fields = ('is_visible', 'order')
        labels = {'is_visible': 'Zichtbaar op de website', 'order': 'Volgorde'}
