from uuid import uuid4
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import MemberProfile


class EmailLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='E-mailadres of gebruikersnaam',
        max_length=254,
        widget=forms.TextInput(attrs={'autocomplete': 'username', 'autofocus': True}),
    )

    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError:
            identifier = (self.cleaned_data.get('username') or '').strip()
            password = self.cleaned_data.get('password')
            if identifier and password:
                User = get_user_model()
                matches = list(User._default_manager.filter(
                    email__iexact=identifier,
                ).exclude(email='')[:2])
                if not matches:
                    matches = list(User._default_manager.filter(
                        username=identifier,
                        email='',
                    )[:2])
                if len(matches) == 1:
                    user = matches[0]
                    if not user.is_active and user.check_password(password):
                        raise forms.ValidationError(
                            'Je account is nog niet geactiveerd. Controleer je '
                            'e-mail en klik op de activatielink voordat je inlogt.',
                            code='inactive',
                        )
            raise


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
    first_name = forms.CharField(label='Voornaam', max_length=150)
    last_name = forms.CharField(label='Achternaam', max_length=150)
    email = forms.EmailField(label='E-mailadres')

    class Meta:
        model = MemberProfile
        fields = ('phone', 'street', 'house_number', 'postal_code', 'city')
        labels = {
            'phone': 'Telefoonnummer', 'street': 'Straat',
            'house_number': 'Huisnummer', 'postal_code': 'Postcode', 'city': 'Woonplaats',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = user
        if user is not None and not self.is_bound:
            self.initial.update(first_name=user.first_name, last_name=user.last_name, email=user.email)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if self.account is not None and get_user_model().objects.exclude(pk=self.account.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError('Dit e-mailadres is al in gebruik.')
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            user = self.account
            user.first_name = self.cleaned_data['first_name'].strip()
            user.last_name = self.cleaned_data['last_name'].strip()
            user.email = self.cleaned_data['email']
            user.save(update_fields=['first_name', 'last_name', 'email'])
        return profile


class MemberDetailsForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ('phone', 'street', 'house_number', 'postal_code', 'city')
        labels = {
            'phone': 'Telefoonnummer', 'street': 'Straat',
            'house_number': 'Huisnummer', 'postal_code': 'Postcode', 'city': 'Woonplaats',
        }


class AccountAccessForm(forms.Form):
    """Only superusers may submit this form; roles are deliberately allowlisted."""
    first_name = forms.CharField(label='Voornaam', max_length=150, required=False)
    last_name = forms.CharField(label='Achternaam', max_length=150, required=False)
    email = forms.EmailField(label='E-mailadres')
    is_active = forms.BooleanField(label='Account actief', required=False)
    role_member = forms.BooleanField(label='Lid', required=False)
    role_trainer = forms.BooleanField(label='Trainer', required=False)
    role_editor = forms.BooleanField(label='Website bewerken', required=False)
    role_admin = forms.BooleanField(label='Administrator', required=False)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and not self.is_bound:
            groups = set(user.groups.values_list('name', flat=True))
            self.initial.update({
                'first_name': user.first_name, 'last_name': user.last_name,
                'email': user.email, 'is_active': user.is_active,
                'role_member': 'MHAV - Lid' in groups,
                'role_trainer': 'MHAV - Trainer' in groups,
                'role_editor': 'MHAV - Websitebeheer' in groups,
                'role_admin': 'MHAV - Administrator' in groups,
            })

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()
