from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

class Season(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Concept'
        ACTIVE = 'active', 'Actief'
        CLOSED = 'closed', 'Afgesloten'
    name = models.CharField('Seizoen', max_length=120, unique=True)
    starts_on = models.DateField('Startdatum')
    ends_on = models.DateField('Einddatum')
    status = models.CharField('Status', max_length=12, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField('Opmerkingen', blank=True)
    class Meta:
        ordering = ('-starts_on',)
    def clean(self):
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError({'ends_on': 'Einddatum moet na de startdatum liggen.'})
    def __str__(self): return self.name

class Dog(models.Model):
    name = models.CharField('Naam hond', max_length=120)
    breed = models.CharField('Ras', max_length=120, blank=True)
    date_of_birth = models.DateField('Geboortedatum', blank=True, null=True)
    notes = models.TextField('Opmerkingen', blank=True)
    class Meta:
        ordering = ('name', 'pk')
    def __str__(self): return self.name

class Combination(models.Model):
    handler = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='dog_combinations', verbose_name='Geleider')
    dog = models.ForeignKey(Dog, on_delete=models.PROTECT, related_name='combinations', verbose_name='Hond')
    notes = models.TextField('Opmerkingen', blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=('handler','dog'), name='unique_mhav_handler_dog')]
        ordering = ('handler__last_name','dog__name')
    def __str__(self): return f'{self.handler.get_full_name() or self.handler.email or self.handler.username} — {self.dog.name}'

class TrainingGroup(models.Model):
    class Day(models.TextChoices):
        MON='mon','Maandag'; TUE='tue','Dinsdag'; WED='wed','Woensdag'; THU='thu','Donderdag'; FRI='fri','Vrijdag'; SAT='sat','Zaterdag'; SUN='sun','Zondag'
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name='groups', verbose_name='Seizoen')
    name = models.CharField('Groepsnaam', max_length=120)
    # Keep legacy names for groups created before linking the catalogue.
    course_name = models.CharField('Cursus / niveau (historisch)', max_length=160, blank=True)
    course = models.ForeignKey('website.SitePage', on_delete=models.PROTECT, related_name='training_groups', null=True, blank=True, verbose_name='Cursusaanbod')
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='planned_training_groups', verbose_name='Instructeur', limit_choices_to={'groups__name': 'MHAV - Trainer'})
    day = models.CharField('Lesdag', max_length=3, choices=Day.choices)
    starts_at = models.TimeField('Begintijd')
    ends_at = models.TimeField('Eindtijd')
    capacity = models.PositiveSmallIntegerField('Maximum deelnemers', default=10)
    notes = models.TextField('Opmerkingen', blank=True)
    class Meta:
        ordering = ('season__starts_on','day','starts_at','name')
        constraints = [models.UniqueConstraint(fields=('season','name'), name='unique_mhav_group_per_season')]
    @property
    def course_title(self):
        return self.course.title if self.course_id else self.course_name

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'Eindtijd moet later zijn dan begintijd.'})
        if self.capacity is not None and self.capacity < 1:
            raise ValidationError({'capacity': 'Kies minimaal 1 deelnemer.'})
        if not self.course_id and not self.course_name.strip():
            raise ValidationError({'course': 'Kies een cursus uit het cursusaanbod.'})

    def __str__(self): return f'{self.season} — {self.name}'

class Enrollment(models.Model):
    class Status(models.TextChoices):
        PLACED='placed','Ingepland'
        WAITING='waiting','Wachtlijst'
        CANCELLED='cancelled','Geannuleerd'
    group = models.ForeignKey(TrainingGroup, on_delete=models.PROTECT, related_name='enrollments', verbose_name='Lesgroep')
    combination = models.ForeignKey(Combination, on_delete=models.PROTECT, related_name='enrollments', verbose_name='Combinatie')
    status = models.CharField('Status', max_length=12, choices=Status.choices, default=Status.PLACED)
    notes = models.TextField('Opmerkingen', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=('group','combination'), name='unique_mhav_enrollment')]
        ordering = ('group','created_at')
    def clean(self):
        if self.group_id and self.combination_id and self.status == self.Status.PLACED:
            occupied = Enrollment.objects.filter(group_id=self.group_id, status=self.Status.PLACED).exclude(pk=self.pk).count()
            if occupied >= self.group.capacity:
                raise ValidationError({'status': 'Deze groep is vol. Gebruik de wachtlijst.'})
    def __str__(self): return f'{self.combination} / {self.group}'
