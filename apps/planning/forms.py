from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Season, Dog, Combination, TrainingGroup, Enrollment, CourseApplication, TrainerSeasonAvailability

class StyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.DateField): field.widget = forms.DateInput(attrs={'type':'date'}, format='%Y-%m-%d')
            if isinstance(field, forms.TimeField): field.widget = forms.TimeInput(attrs={'type':'time'}, format='%H:%M')
            field.widget.attrs.setdefault('class','mhav-planning-input')

class SeasonForm(StyledForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and not self.is_bound:
            self.initial['lesson_day'] = 'sat'

    class Meta:
        model=Season; fields=('name','starts_on','lesson_count','lesson_day','status','notes')

    def save(self, commit=True):
        instance = super().save(commit=False)
        dates = instance.lesson_dates
        if dates:
            instance.ends_on = dates[-1]
        if commit:
            instance.save()
        return instance

class DogForm(StyledForm):
    class Meta:
        model=Dog; fields=('name','breed','date_of_birth','notes')

class CombinationForm(StyledForm):
    class Meta:
        model=Combination; fields=('handler','dog','notes')
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['handler'].queryset=get_user_model().objects.filter(is_active=True).order_by('last_name','first_name','email')
        self.fields['handler'].label_from_instance=lambda u: f'{u.get_full_name() or u.email or u.username} ({u.email})'

class TrainingGroupForm(StyledForm):
    lesson_dates_selected = forms.MultipleChoiceField(
        label='Lesdagen (zaterdagen)', required=True,
        widget=forms.CheckboxSelectMultiple,
        help_text='Vink de zaterdagen aan waarop deze groep daadwerkelijk les heeft.',
    )

    class Meta:
        model = TrainingGroup
        fields = ('name', 'course', 'starts_at', 'ends_at', 'capacity',
                  'lesson_dates_selected', 'trainer', 'notes')
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.website.models import SitePage
        from apps.website.views import TRAINING_SLUGS
        self.season = season or (self.instance.season if self.instance.pk else None)
        if self.season is None:
            raise ValueError('A season is required to edit a lesson group.')
        courses = SitePage.objects.filter(
            Q(slug__in=TRAINING_SLUGS) | Q(slug__startswith='cursus-')
        ).exclude(slug='phv-knpv')
        if self.instance.pk and self.instance.course_id:
            courses = courses.filter(Q(is_published=True) | Q(pk=self.instance.course_id))
        else:
            courses = courses.filter(is_published=True)
        self.fields['course'].queryset = courses.order_by('menu_order', 'title')
        self.fields['course'].required = True
        eligible_ids = [
            response.trainer_id
            for response in TrainerSeasonAvailability.objects.filter(season=self.season)
            if response.available_count > 0
        ]
        self.fields['trainer'].queryset = get_user_model().objects.filter(
            is_active=True, groups__name='MHAV - Trainer', pk__in=eligible_ids
        ).distinct().order_by('last_name', 'first_name')
        self.fields['trainer'].label_from_instance = lambda u: u.get_full_name() or u.email or u.username
        self.fields['trainer'].required = False
        self.fields['trainer'].empty_label = 'Nog geen instructeur toegewezen'
        self.fields['lesson_dates_selected'].choices = [
            (day.isoformat(), day.strftime('%d-%m-%Y')) for day in self.season.lesson_dates
        ]
        if not self.is_bound and self.instance.pk:
            self.initial['lesson_dates_selected'] = self.instance.lesson_dates_selected
        elif not self.is_bound:
            self.initial['lesson_dates_selected'] = [
                day.isoformat() for day in self.season.lesson_dates
            ]
        self.fields['name'].label = 'Groepsnaam'
        self.fields['course'].label = 'Cursus'
        self.fields['starts_at'].label = 'Starttijd'
        self.fields['ends_at'].label = 'Eindtijd'
        self.fields['capacity'].label = 'Maximum deelnemers'
        self.fields['trainer'].label = 'Instructeur'

    def save(self, commit=True):
        group = super().save(commit=False)
        group.season = self.season
        group.day = TrainingGroup.Day.SAT
        group.lesson_dates_selected = sorted(self.cleaned_data['lesson_dates_selected'])
        if commit:
            group.save()
        return group

    def _post_clean(self):
        self.instance.day = TrainingGroup.Day.SAT
        super()._post_clean()


class EnrollmentForm(StyledForm):
    class Meta:
        model=Enrollment; fields=('group','combination','status','notes')
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['combination'].queryset=Combination.objects.select_related('handler','dog').all()


class CourseApplicationForm(StyledForm):
    privacy_agreement = forms.BooleanField(label='Ik heb de privacyverklaring gelezen en ga akkoord met de verwerking van mijn gegevens voor deze inschrijving.')
    website = forms.CharField(required=False, widget=forms.HiddenInput)  # Honeypot
    existing_dog = forms.ModelChoiceField(queryset=Dog.objects.none(), required=False, label='Mijn bestaande hond', empty_label='Nieuwe hond aanmelden', help_text='Kies een hond uit je Mijn MHAV-profiel, of laat dit leeg voor een nieuwe hond.')

    class Meta:
        model = CourseApplication
        fields = ('first_name','middle_name','last_name','email','phone','street','house_number','postal_code','city','country',
                  'dog_name','dog_breed','dog_birth_date','dog_sex','dog_origin','dog_pedigree','dog_notes','second_handler_name','start_preference','season','course',
                  'dog_count','first_dog','trained_before','experience','availability','remarks')
        widgets = {
            'dog_notes': forms.Textarea(attrs={'rows':3}),
            'experience': forms.Textarea(attrs={'rows':3}),
            'availability': forms.Textarea(attrs={'rows':3}),
            'remarks': forms.Textarea(attrs={'rows':3}),
        }

    def __init__(self, *args, **kwargs):
        self.applicant_user = kwargs.pop('applicant_user', None)
        super().__init__(*args, **kwargs)
        if self.applicant_user is not None and self.applicant_user.is_authenticated:
            # Disabled Django fields always validate from initial values, not POST.
            # This prevents forged requests from changing the applicant identity.
            identity = {
                'first_name': self.applicant_user.first_name,
                'middle_name': '',
                'last_name': self.applicant_user.last_name,
                'email': self.applicant_user.email,
            }
            for name, value in identity.items():
                self.fields[name].initial = value
                self.initial[name] = value
                self.fields[name].disabled = True
        if self.applicant_user is not None and self.applicant_user.is_authenticated:
            self.fields['existing_dog'].queryset = Dog.objects.filter(combinations__handler=self.applicant_user).distinct().order_by('name', 'pk')
        else:
            self.fields.pop('existing_dog')
        from apps.website.models import SitePage
        from apps.website.views import TRAINING_SLUGS
        from .models import SeasonCourseOffering
        open_offerings = [o for o in SeasonCourseOffering.objects.select_related('season', 'course').all() if o.accepts_applications()]
        # Backward compatibility: older registration clients do not send this field.
        self.fields['start_preference'].required = False
        self.fields['season'].queryset = Season.objects.filter(pk__in=[o.season_id for o in open_offerings])
        self.fields['season'].required = False
        self.fields['season'].empty_label = 'Geen voorkeur / nog niet bekend'
        self.fields['course'].queryset = SitePage.objects.filter(is_published=True).filter(
            Q(slug__in=TRAINING_SLUGS) | Q(slug__startswith='cursus-')
        ).exclude(slug='phv-knpv').order_by('menu_order', 'title')
        self.fields['course'].required = True
        self.fields['course'].empty_label = 'Kies een cursus'
        self.fields['dog_name'].required = False
        self.fields['dog_birth_date'].required = False
        self.fields['dog_birth_date'].help_text = 'Als de geboortedatum niet bekend is, mag dit leeg blijven.'
        self.fields['dog_breed'].required = False
        self.fields['dog_sex'].choices = [('', 'Onbekend')] + list(self.fields['dog_sex'].choices)[1:]
        self.fields['availability'].help_text = 'Welke dagen en tijden passen? Vermeld ook wanneer je niet kunt.'
        self.fields['dog_notes'].help_text = 'Bijvoorbeeld angst, reactiviteit of een lichamelijke beperking. Deel alleen wat relevant is voor de training.'

    def clean(self):
        data = super().clean()
        if self.applicant_user is not None and self.applicant_user.is_authenticated:
            if not (self.applicant_user.first_name.strip() and self.applicant_user.last_name.strip() and self.applicant_user.email.strip()):
                raise forms.ValidationError('Vul eerst je voornaam, achternaam en e-mailadres aan in je MHAV-account voordat je je aanmeldt.')
        dog = data.get('existing_dog')
        if not dog and not (data.get('dog_name') or '').strip():
            self.add_error('dog_name', 'Vul de naam van de hond in of kies een bestaande hond.')
        if dog:
            # Never trust posted dog identity fields when an existing profile is selected.
            data['dog_name'] = dog.name
            data['dog_breed'] = dog.breed
            data['dog_birth_date'] = dog.date_of_birth
        preference = data.get('start_preference')
        season, course = data.get('season'), data.get('course')
        if not preference and 'start_preference' not in self.data:
            # Legacy submissions: a selected season means an explicit request.
            preference = (CourseApplication.StartPreference.SPECIFIC if season
                          else CourseApplication.StartPreference.FLEXIBLE)
            data['start_preference'] = preference
        elif not preference:
            self.add_error('start_preference', 'Kies wanneer je wilt beginnen.')
        if preference == CourseApplication.StartPreference.SPECIFIC and not season:
            self.add_error('season', 'Kies het seizoen waarin je bij voorkeur wilt starten.')
        if preference != CourseApplication.StartPreference.SPECIFIC and season:
            self.add_error('season', 'Kies alleen een seizoen wanneer je een specifieke cursusperiode wilt.')

        if season and course:
            from .models import SeasonCourseOffering
            offering = SeasonCourseOffering.objects.filter(season=season, course=course).first()
            if not offering or not offering.accepts_applications():
                raise forms.ValidationError('Deze cursus is momenteel niet open voor inschrijving in dit seizoen.')
        if season and not course:
            raise forms.ValidationError('Kies een cursus bij dit seizoen.')
        return data

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Aanmelding kon niet worden verwerkt.')
        return ''

    def clean_dog_birth_date(self):
        from django.utils import timezone
        value = self.cleaned_data.get('dog_birth_date')
        if value and value > timezone.localdate():
            raise forms.ValidationError('De geboortedatum kan niet in de toekomst liggen.')
        return value


class ApplicationReviewForm(StyledForm):
    class Meta:
        model = CourseApplication
        fields = ('status','admin_notes')
        widgets = {'admin_notes': forms.Textarea(attrs={'rows':4})}


class TrainerAvailabilityForm(forms.ModelForm):
    class Meta:
        model = TrainerSeasonAvailability
        fields = ('response', 'notes')
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}
