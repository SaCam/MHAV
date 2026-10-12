from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Season, Dog, Combination, TrainingGroup, Enrollment

class StyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.DateField): field.widget = forms.DateInput(attrs={'type':'date'}, format='%Y-%m-%d')
            if isinstance(field, forms.TimeField): field.widget = forms.TimeInput(attrs={'type':'time'}, format='%H:%M')
            field.widget.attrs.setdefault('class','mhav-planning-input')

class SeasonForm(StyledForm):
    class Meta:
        model=Season; fields=('name','starts_on','ends_on','status','notes')

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
    class Meta:
        model=TrainingGroup; fields=('season','name','course','trainer','day','starts_at','ends_at','capacity','notes')
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        from apps.website.models import SitePage
        from apps.website.views import TRAINING_SLUGS
        course_qs = SitePage.objects.filter(Q(slug__in=TRAINING_SLUGS) | Q(slug__startswith="cursus-")).exclude(slug="phv-knpv")
        self.fields['course'].queryset = course_qs.filter(is_published=True).order_by('menu_order', 'title')
        if self.instance.pk and self.instance.course_id:
            self.fields['course'].queryset = course_qs.filter(
                Q(is_published=True) | Q(pk=self.instance.course_id)
            ).order_by('menu_order', 'title')
        self.fields['course'].required = True
        self.fields['trainer'].queryset=get_user_model().objects.filter(is_active=True,groups__name='MHAV - Trainer').distinct().order_by('last_name','first_name')
        self.fields['trainer'].label_from_instance=lambda u: u.get_full_name() or u.email or u.username

class EnrollmentForm(StyledForm):
    class Meta:
        model=Enrollment; fields=('group','combination','status','notes')
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['combination'].queryset=Combination.objects.select_related('handler','dog').all()
