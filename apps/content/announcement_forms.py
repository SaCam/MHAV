from django import forms
from .models import Announcement

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ('title', 'body', 'priority', 'is_published', 'published_at', 'expires_at')
        widgets = {'published_at': forms.DateTimeInput(attrs={'type':'datetime-local'}, format='%Y-%m-%dT%H:%M'), 'expires_at': forms.DateTimeInput(attrs={'type':'datetime-local'}, format='%Y-%m-%dT%H:%M')}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['published_at'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']
        self.fields['expires_at'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S']
    def clean(self):
        data = super().clean()
        if data.get('expires_at') and data.get('published_at') and data['expires_at'] <= data['published_at']:
            self.add_error('expires_at', 'De einddatum moet na de publicatiedatum liggen.')
        return data
