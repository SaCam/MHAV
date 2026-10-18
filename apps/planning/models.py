from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from datetime import timedelta

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
    lesson_count = models.PositiveSmallIntegerField('Aantal lessen', default=10)
    lesson_day = models.CharField('Lesdag', max_length=3, choices=[('sun', 'Zondag'), ('mon', 'Maandag'), ('tue', 'Dinsdag'), ('wed', 'Woensdag'), ('thu', 'Donderdag'), ('fri', 'Vrijdag'), ('sat', 'Zaterdag')], default='sun')

    @property
    def lesson_dates(self):
        if not self.starts_on or not self.lesson_count:
            return []
        day_numbers = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
        first = self.starts_on + timedelta(days=(day_numbers[self.lesson_day] - self.starts_on.weekday()) % 7)
        return [first + timedelta(weeks=i) for i in range(self.lesson_count)]

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
    photo = models.ImageField('Foto hond', upload_to='dogs/%Y/%m/', blank=True, null=True)
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
    lesson_dates_selected = models.JSONField('Geplande leszaterdagen', default=list, blank=True)
    class ExecutionStatus(models.TextChoices):
        PLANNED = 'planned', 'Gepland'
        ACTIVE = 'active', 'Bezig'
        COMPLETED = 'completed', 'Afgerond'
        CANCELLED = 'cancelled', 'Geannuleerd'
    execution_status = models.CharField('Uitvoering', max_length=12, choices=ExecutionStatus.choices, default=ExecutionStatus.PLANNED)
    execution_started_at = models.DateTimeField(null=True, blank=True)
    execution_closed_at = models.DateTimeField(null=True, blank=True)
    execution_closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='closed_mhav_groups')
    planning_locked_at = models.DateTimeField('Conceptplanning goedgekeurd op', null=True, blank=True)
    planning_locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_mhav_group_plans')
    class Meta:
        ordering = ('season__starts_on','day','starts_at','name')
        constraints = [models.UniqueConstraint(fields=('season','name'), name='unique_mhav_group_per_season')]
    @property
    def course_title(self):
        return self.course.title if self.course_id else self.course_name

    @property
    def scheduled_dates(self):
        from datetime import date
        return [date.fromisoformat(day) for day in self.lesson_dates_selected]

    @property
    def first_lesson_date(self):
        """Earliest actual scheduled lesson; never infer from the weekday or season start."""
        return min(self.scheduled_dates, default=None)

    def clean(self):
        super().clean()
        if self.day != self.Day.SAT:
            raise ValidationError({'day': 'Lesgroepen worden uitsluitend op zaterdag gepland.'})
        if self.season_id:
            allowed = {day.isoformat() for day in self.season.lesson_dates}
            if self.season.lesson_day != 'sat':
                raise ValidationError('Stel de lesdag van dit seizoen eerst in op zaterdag.')
            if (not isinstance(self.lesson_dates_selected, list)
                    or not self.lesson_dates_selected
                    or len(set(self.lesson_dates_selected)) != len(self.lesson_dates_selected)
                    or any(day not in allowed for day in self.lesson_dates_selected)):
                raise ValidationError('Selecteer minimaal één geldige zaterdag uit het seizoen.')
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'Eindtijd moet later zijn dan begintijd.'})
        if self.capacity is not None and self.capacity < 1:
            raise ValidationError({'capacity': 'Kies minimaal 1 deelnemer.'})
        if not self.course_id and not self.course_name.strip():
            raise ValidationError({'course': 'Kies een cursus uit het cursusaanbod.'})

    def __str__(self): return f'{self.season} — {self.name}'

class LessonInstructorOverride(models.Model):
    """One-off instructor assignment; confirmation is recorded by a planner offline."""
    group = models.ForeignKey(TrainingGroup, on_delete=models.CASCADE, related_name='instructor_overrides')
    lesson_date = models.DateField('Lesdatum')
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='lesson_substitutions', limit_choices_to={'groups__name': 'MHAV - Trainer'})
    offline_confirmed = models.BooleanField('Offline bevestigd', default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('group', 'lesson_date'), name='unique_mhav_lesson_instructor_override')]

    def clean(self):
        super().clean()
        if self.group_id and self.lesson_date.isoformat() not in self.group.lesson_dates_selected:
            raise ValidationError({'lesson_date': 'Deze datum is geen geplande lesdag.'})
        if self.trainer_id and (not self.trainer.is_active or not self.trainer.groups.filter(name='MHAV - Trainer').exists()):
            raise ValidationError({'trainer': 'Selecteer een actieve MHAV-instructeur.'})


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
    class Outcome(models.TextChoices):
        PENDING = 'pending', 'In opleiding'
        COMPLETED = 'completed', 'Afgerond'
        STOPPED = 'stopped', 'Gestopt'
        NOT_COMPLETED = 'not_completed', 'Niet afgerond'
    outcome = models.CharField('Eindresultaat', max_length=16, choices=Outcome.choices, default=Outcome.PENDING)
    capacity_override_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='mhav_capacity_exceptions')
    capacity_override_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=('group','combination'), name='unique_mhav_enrollment')]
        ordering = ('group','created_at')
    def clean(self):
        if self.group_id and self.combination_id and self.status == self.Status.PLACED:
            occupied = Enrollment.objects.filter(group_id=self.group_id, status=self.Status.PLACED).exclude(pk=self.pk).count()
            if occupied >= self.group.capacity and not self.capacity_override_by_id:
                raise ValidationError({'status': 'Deze groep is vol. Gebruik de wachtlijst.'})
    def __str__(self): return f'{self.combination} / {self.group}'


class CourseApplication(models.Model):
    """Public intake request; not a confirmed place or a member account."""
    class Status(models.TextChoices):
        NEW = 'new', 'Nieuw'
        REVIEW = 'review', 'In behandeling'
        WAITING = 'waiting', 'Wacht op indeling'
        PROCESSED = 'processed', 'Verwerkt'
        REJECTED = 'rejected', 'Niet geplaatst / ingetrokken'
        WAITLIST = 'waitlist', 'Wachtlijst'

    created_at = models.DateTimeField('Ontvangen op', auto_now_add=True)
    updated_at = models.DateTimeField('Bijgewerkt op', auto_now=True)
    status = models.CharField('Status', max_length=12, choices=Status.choices, default=Status.NEW)
    confirmation_email_status = models.CharField('Bevestigingsmail', max_length=12, choices=[('not_sent', 'Nog niet verzonden'), ('sent', 'Verzonden'), ('failed', 'Verzenden mislukt')], default='not_sent')
    confirmation_email_sent_at = models.DateTimeField('Bevestigingsmail verzonden op', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='course_applications')
    identity_verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_course_applications')
    identity_verified_at = models.DateTimeField(null=True, blank=True)
    identity_verification_method = models.CharField(max_length=32, blank=True, choices=[('in_person', 'Persoonlijk gecontroleerd'), ('video_call', 'Videogesprek'), ('authenticated_contact', 'Gecontroleerd contactkanaal')])
    identity_verification_reference = models.CharField(max_length=500, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_course_applications', verbose_name='Ingediend door')
    submission_source = models.CharField('Inschrijfkanaal', max_length=12, choices=[('guest', 'Gast'), ('member', 'Mijn MHAV'), ('admin', 'Beheerder')], default='guest')
    first_name = models.CharField('Voornaam', max_length=100)
    last_name = models.CharField('Achternaam', max_length=120)
    email = models.EmailField('E-mailadres')
    phone = models.CharField('Telefoonnummer', max_length=35)
    street = models.CharField('Straat', max_length=160)
    house_number = models.CharField('Huisnummer', max_length=20)
    postal_code = models.CharField('Postcode', max_length=16)
    city = models.CharField('Woonplaats', max_length=120)
    middle_name = models.CharField('Tussenvoegsel', max_length=60, blank=True)
    country = models.CharField('Land', max_length=30, choices=[('NL','Nederland'),('BE','België'),('OTHER','Anders')], default='NL')
    dog_origin = models.CharField('Herkomst hond', max_length=20, choices=[('breeder','Fokker'),('private','Particulier'),('shelter','Asiel'),('other','Anders')], blank=True)
    dog_pedigree = models.BooleanField('Rashond met stamboom', null=True, blank=True)
    dog_count = models.CharField('Aantal honden', max_length=12, choices=[('one','Eén hond'),('two','Twee honden'),('more','Meer dan twee')], blank=True)
    first_dog = models.BooleanField('Is dit uw eerste hond?', null=True, blank=True)
    trained_before = models.BooleanField('Eerder hondentraining gevolgd?', null=True, blank=True)
    time_preferences = models.JSONField('Beschikbaarheid per lesmoment', default=dict, blank=True)
    dog_name = models.CharField('Naam hond', max_length=120)
    dog_breed = models.CharField('Ras / kruising', max_length=120)
    dog_birth_date = models.DateField('Geboortedatum hond', null=True, blank=True)
    dog_sex = models.CharField('Geslacht hond', max_length=12, choices=[('male','Reu'),('female','Teef')], blank=True)
    dog_notes = models.TextField('Bijzonderheden hond', blank=True)
    season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    course = models.ForeignKey('website.SitePage', on_delete=models.SET_NULL, null=True, blank=True, related_name='course_applications')
    experience = models.TextField('Eerdere training / niveau', blank=True)
    availability = models.TextField('Beschikbaarheid / voorkeur', blank=True)
    remarks = models.TextField('Overige opmerkingen', blank=True)
    privacy_accepted_at = models.DateTimeField('Privacyverklaring akkoord op')
    admin_notes = models.TextField('Interne opmerkingen', blank=True)
    second_handler_name = models.CharField('Tweede geleider (naam)', max_length=200, blank=True)
    dog_profile = models.ForeignKey(Dog, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_applications')
    linked_combination = models.ForeignKey(Combination, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_applications')
    linked_enrollment = models.ForeignKey(Enrollment, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_applications')
    class Outcome(models.TextChoices):
        PENDING = 'pending', 'In opleiding'
        COMPLETED = 'completed', 'Afgerond'
        STOPPED = 'stopped', 'Gestopt'
        NOT_COMPLETED = 'not_completed', 'Niet afgerond'
    outcome = models.CharField('Eindresultaat', max_length=16, choices=Outcome.choices, default=Outcome.PENDING)
    capacity_override_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='mhav_draft_capacity_exceptions')
    capacity_override_at = models.DateTimeField(null=True, blank=True)
    placement_source = models.CharField('Herkomst conceptplaatsing', max_length=12, choices=[('legacy', 'Onbekend (bestaand)'), ('manual', 'Handmatig'), ('automatic', 'Automatisch')], default='legacy')
    proposed_group = models.ForeignKey(TrainingGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='proposed_applications', verbose_name='Voorlopige lesgroep')
    closure_reason = models.CharField('Afhandelreden', max_length=24, blank=True, choices=[('capacity', 'Geen beschikbare plaats'), ('availability', 'Geen passend lesmoment'), ('withdrawn', 'Ingetrokken door aanvrager'), ('other', 'Overige reden')])
    closure_note = models.TextField('Toelichting afhandeling', blank=True)
    handled_at = models.DateTimeField('Afgehandeld op', null=True, blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_mhav_applications')

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Cursusaanmelding'
        verbose_name_plural = 'Cursusaanmeldingen'

    def __str__(self):
        return f'{self.first_name} {self.last_name} — {self.dog_name}'


class TrainerSeasonAvailability(models.Model):
    """Trainer response to an upcoming season; never assigns a lesson group."""

    class Response(models.TextChoices):
        ALL = 'all', 'Alle lesdagen beschikbaar'
        PARTIAL = 'partial', 'Gedeeltelijk beschikbaar'
        NONE = 'none', 'Niet beschikbaar'

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='trainer_availabilities')
    trainer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='season_availabilities')
    response = models.CharField('Beschikbaarheid', max_length=10, choices=Response.choices)
    unavailable_dates = models.JSONField('Niet beschikbare lesdata', default=list, blank=True)
    date_statuses = models.JSONField('Status per lesdatum', default=dict, blank=True)
    notes = models.TextField('Opmerkingen', blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('season', 'trainer'), name='unique_mhav_trainer_season_availability')]

    def clean(self):
        super().clean()
        allowed = {day.isoformat() for day in self.season.lesson_dates} if self.season_id else set()
        if not isinstance(self.unavailable_dates, list) or any(
            day not in allowed for day in self.unavailable_dates
        ):
            raise ValidationError('Selecteer uitsluitend lesdata uit dit seizoen.')
        if not isinstance(self.date_statuses, dict) or any(
            day not in allowed or state not in ('yes', 'no', 'maybe', 'unset')
            for day, state in self.date_statuses.items()
        ):
            raise ValidationError('Ongeldige beschikbaarheid voor een lesdatum.')
        # Legacy unavailable_dates is retained for existing records. With the
        # per-date status system, a 'none' response legitimately marks every
        # lesson as unavailable, so it must not be rejected here.
        # Validate consistency using date_statuses instead.
        if self.response == self.Response.ALL and any(
            state != 'yes' for state in self.date_statuses.values()
        ):
            raise ValidationError('Alle lesdagen moeten beschikbaar zijn.')
        if self.response == self.Response.NONE and any(
            state != 'no' for state in self.date_statuses.values()
        ):
            raise ValidationError('Alle lesdagen moeten niet beschikbaar zijn.')

    def status_for_date(self, day):
        key = day.isoformat() if hasattr(day, 'isoformat') else str(day)
        if self.response == self.Response.ALL:
            return 'yes'
        if self.response == self.Response.NONE:
            return 'no'
        if key in self.date_statuses:
            return self.date_statuses[key]
        return 'no' if key in self.unavailable_dates else 'maybe'

    @property
    def available_count(self):
        return sum(self.status_for_date(day) == 'yes' for day in self.season.lesson_dates)


class SeasonCourseOffering(models.Model):
    """Approval and registration gate for one course in one season."""
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='course_offerings')
    course = models.ForeignKey('website.SitePage', on_delete=models.PROTECT, related_name='season_offerings')
    approved = models.BooleanField('Planning goedgekeurd', default=False)
    coverage_override = models.BooleanField('Dekkingstekort geaccepteerd', default=False)
    override_reason = models.TextField('Reden uitzondering', blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_course_offerings')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_signature = models.CharField(max_length=64, blank=True)
    registration_open = models.BooleanField('Inschrijving open', default=False)
    registration_opens_at = models.DateTimeField(null=True, blank=True)
    registration_closes_at = models.DateTimeField(null=True, blank=True)
    waiting_list_enabled = models.BooleanField('Wachtlijst toestaan', default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('season', 'course'), name='unique_mhav_season_course_offering')]
        ordering = ('season__starts_on', 'course__title')

    def __str__(self):
        return f'{self.season} — {self.course}'

    def planning_snapshot(self):
        import hashlib
        import json
        groups = list(TrainingGroup.objects.filter(season=self.season, course=self.course)
                      .select_related('trainer').prefetch_related('instructor_overrides'))
        responses = {r.trainer_id: r for r in TrainerSeasonAvailability.objects.filter(season=self.season)}
        issues = []
        uncovered = []
        if not self.course.is_published:
            issues.append('De cursus is niet gepubliceerd in Cursusbeheer.')
        if self.season.status == Season.Status.CLOSED:
            issues.append('Het seizoen is afgesloten.')
        if self.season.lesson_day != 'sat':
            issues.append('Het seizoen moet op zaterdag zijn ingepland.')
        if not groups:
            issues.append('Maak minimaal één lesgroep aan.')
        payload = [self.season.lesson_day, self.season.starts_on.isoformat(), self.season.ends_on.isoformat(), self.season.lesson_count, self.course.is_published]
        allowed = {d.isoformat() for d in self.season.lesson_dates}
        for group in groups:
            dates = sorted(group.lesson_dates_selected or [])
            overrides = {o.lesson_date.isoformat(): o for o in group.instructor_overrides.all()}
            payload.append([group.pk, group.name, group.course_id, group.day, str(group.starts_at), str(group.ends_at), group.capacity, group.trainer_id, dates])
            if not group.name or not group.starts_at or not group.ends_at or group.ends_at <= group.starts_at or group.capacity < 1 or group.day != 'sat' or not dates or any(d not in allowed for d in dates):
                issues.append(f'{group.name}: lesdata, tijden of capaciteit zijn niet correct.')
            if not group.trainer_id:
                issues.append(f'{group.name}: geen hoofdinstructeur toegewezen.')
            response = responses.get(group.trainer_id)
            for day in dates:
                replacement = overrides.get(day)
                state = response.status_for_date(day) if response else 'unset'
                payload.append([group.pk, day, state, replacement.trainer_id if replacement else None, replacement.offline_confirmed if replacement else None])
                if not (replacement.offline_confirmed if replacement else state == 'yes'):
                    uncovered.append(f'{group.name} — {day}')
        signature = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        return {'issues': issues, 'uncovered': uncovered, 'groups': groups, 'signature': signature,
                'structurally_ready': not issues, 'fully_covered': not uncovered}

    def approval_valid(self, snapshot=None):
        snapshot = snapshot or self.planning_snapshot()
        return (self.approved and self.approval_signature == snapshot['signature']
                and not snapshot['issues'] and (not snapshot['uncovered'] or (self.coverage_override and bool(self.override_reason.strip()))))

    def accepts_applications(self, now=None):
        from django.utils import timezone
        now = now or timezone.now()
        if not self.registration_open or not self.approval_valid():
            return False
        if self.registration_opens_at and now < self.registration_opens_at:
            return False
        if self.registration_closes_at and now >= self.registration_closes_at:
            return False
        return True


class LessonRecord(models.Model):
    class Attendance(models.TextChoices):
        UNKNOWN = 'unknown', 'Nog niet ingevuld'
        PRESENT = 'present', 'Aanwezig'
        ABSENT = 'absent', 'Afwezig'
        EXCUSED = 'excused', 'Afgemeld'
    class Rating(models.TextChoices):
        NONE = '', 'Niet beoordeeld'
        ATTENTION = 'attention', 'Aandacht nodig'
        GOOD = 'good', 'Goed'
        EXCELLENT = 'excellent', 'Uitstekend'
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='lesson_records')
    lesson_date = models.DateField('Lesdatum')
    attendance = models.CharField('Aanwezigheid', max_length=10, choices=Attendance.choices, default=Attendance.UNKNOWN)
    rating = models.CharField('Beoordeling', max_length=12, choices=Rating.choices, blank=True, default='')
    notes = models.TextField('Lesnotities', blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=('enrollment', 'lesson_date'), name='unique_mhav_lesson_record')]
        ordering = ('lesson_date', 'enrollment_id')
