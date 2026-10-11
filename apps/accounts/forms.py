from uuid import uuid4
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import MemberProfile


class EmailLoginForm(AuthenticationForm):
    username = forms.CharField(label='E-mailadres of gebruikersnaam', max_length=254, widget=forms.TextInput(attrs={'autocomplete': 'username', 'autofocus': True}))


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(label='Voornaam', max_length=150)
    last_name = forms.CharField(label='Achternaam', max_length=150)
    email = forms.EmailField(label='E-mailadres')

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Dit e-mailadres is al in gebruik.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = 'mhav_' + uuid4().hex[:24]
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            MemberProfile.objects.get_or_create(user=user)
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ('phone',)
        labels = {'phone': 'Telefoonnummer'}


class AccountAccessForm(forms.Form):
    """Only superusers may submit this form; roles are deliberately allowlisted."""
    first_name = forms.CharField(label='Voornaam', max_length=150, required=False)
    last_name = forms.CharField(label='Achternaam', max_length=150, required=False)
    email = forms.EmailField(label='E-mailadres')
    is_active = forms.BooleanField(label='Account actief', required=False)
    is_approved = forms.BooleanField(label='Lidmaatschap goedgekeurd', required=False)
    role_member = forms.BooleanField(label='Lid', required=False)
    role_trainer = forms.BooleanField(label='Trainer', required=False)
    role_editor = forms.BooleanField(label='Website bewerken', required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not self.is_bound:
            groups = set(user.groups.values_list('name', flat=True))
            profile, _ = MemberProfile.objects.get_or_create(user=user)
            self.initial.update({
                'first_name': user.first_name, 'last_name': user.last_name,
                'email': user.email, 'is_active': user.is_active,
                'is_approved': profile.is_approved,
                'role_member': 'MHAV - Lid' in groups,
                'role_trainer': 'MHAV - Trainer' in groups,
                'role_editor': 'MHAV - Websitebeheer' in groups,
            })

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()
