"""Create clearly marked fictitious course applications for testing v21f planning."""
import random
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.planning.models import CourseApplication, Season, TrainingGroup

FIRST = ['Noor', 'Daan', 'Lotte', 'Sem', 'Emma', 'Bram', 'Fleur', 'Milan', 'Sophie', 'Jesse', 'Tess', 'Ruben']
LAST = ['Jansen', 'De Vries', 'Bakker', 'Van Dijk', 'Smit', 'Visser', 'Meijer', 'Bos', 'Mulder', 'Peters']
DOGS = ['Max', 'Luna', 'Bobby', 'Nova', 'Rocky', 'Milo', 'Bella', 'Nala', 'Dex', 'Pip', 'Koda', 'Fenna']
BREEDS = ['Labrador', 'Border collie', 'Mechelse herder', 'Golden retriever', 'Kruising', 'Australian shepherd']
MARKER = '[MHAV TESTDATA - seed_test_applications]'

class Command(BaseCommand):
    help = 'Maak fictieve aanvragen om automatische cursusplanning te testen (geen echte persoonsgegevens).'

    def add_arguments(self, parser):
        parser.add_argument('--season', type=int, required=True, help='ID van bestaand seizoen')
        parser.add_argument('--count', type=int, default=30, help='Aantal testaanvragen (standaard 30)')
        parser.add_argument('--seed', type=int, default=42, help='Reproduceerbare willekeurige verdeling')
        parser.add_argument('--preview', action='store_true', help='Toon selectie zonder iets aan te maken')
        parser.add_argument('--delete-test-data', action='store_true', help='Verwijder alleen aanvragen met de testmarker, mits niet verwerkt/gekoppeld')

    def handle(self, *args, **opts):
        season = Season.objects.filter(pk=opts['season']).first()
        if season is None:
            raise CommandError('Seizoen bestaat niet. Controleer --season ID.')
        if opts['delete_test_data']:
            qs = CourseApplication.objects.filter(season=season, admin_notes__startswith=MARKER,
                linked_enrollment__isnull=True, linked_combination__isnull=True)
            n = qs.count()
            if not opts['preview']:
                qs.delete()
            self.stdout.write(f'{n} testaanvragen {"gevonden" if opts["preview"] else "verwijderd"}.')
            return
        count = opts['count']
        if count < 1 or count > 1000:
            raise CommandError('--count moet tussen 1 en 1000 liggen.')
        groups = list(TrainingGroup.objects.filter(season=season, course__isnull=False, course__is_published=True)
                      .select_related('course').order_by('course_id', 'starts_at', 'pk'))
        if not groups:
            raise CommandError('Geen lesgroepen met gepubliceerde cursus in dit seizoen. Maak die eerst aan.')
        by_course = {}
        for group in groups:
            by_course.setdefault(group.course_id, []).append(group)
        rng = random.Random(opts['seed'])
        self.stdout.write(f'Seizoen: {season.name}; {len(groups)} lesgroepen; {len(by_course)} cursussen; {count} testaanvragen.')
        if opts['preview']:
            self.stdout.write('Preview: niets opgeslagen.')
            return
        now = timezone.now()
        course_ids = list(by_course)
        with transaction.atomic():
            for i in range(count):
                course_id = course_ids[i % len(course_ids)]
                course_groups = by_course[course_id]
                preferred = rng.choice(course_groups)
                # Realistic mix: mostly one preferred slot, sometimes alternative options.
                preferences = {str(preferred.pk): 'preferred'}
                for group in course_groups:
                    if group.pk != preferred.pk:
                        preferences[str(group.pk)] = rng.choices(['ok', 'unavailable'], weights=[65, 35])[0]
                first = rng.choice(FIRST)
                last = rng.choice(LAST)
                dog = rng.choice(DOGS)
                application = CourseApplication.objects.create(
                    first_name=first, last_name=last,
                    email=f'mhav-test-{opts["seed"]}-{i+1}@example.com', phone='0612345678',
                    street='Teststraat', house_number=str(i + 1), postal_code='1234 AB',
                    city='Testdorp', country='NL', dog_name=dog, dog_breed=rng.choice(BREEDS),
                    dog_sex=rng.choice(['male', 'female']), season=season, course_id=course_id,
                    status=CourseApplication.Status.NEW, time_preferences=preferences,
                    availability='Testaanvraag: zie beschikbaarheid per lesgroep.',
                    privacy_accepted_at=now,
                    admin_notes=f'{MARKER} Fictieve data voor automatische-planningstest.',
                )
                # Backdate to create a clear FIFO order; auto_now_add requires a separate update.
                CourseApplication.objects.filter(pk=application.pk).update(
                    created_at=now - timedelta(days=count - i, minutes=rng.randint(0, 59))
                )
        self.stdout.write(self.style.SUCCESS(f'{count} fictieve aanvragen aangemaakt. Open Inschrijfaanvragen → Plan automatisch.'))
        self.stdout.write('Verwijderen: python manage.py seed_test_applications --season '
                          f'{season.pk} --delete-test-data')
