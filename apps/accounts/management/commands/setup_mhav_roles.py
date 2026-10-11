from django.core.management.base import BaseCommand
from apps.accounts.roles import ensure_roles

class Command(BaseCommand):
    help = 'Maak MHAV-rollen aan en synchroniseer hun rechten.'

    def handle(self, *args, **options):
        ensure_roles()
        self.stdout.write(self.style.SUCCESS('MHAV-rollen zijn ingesteld.'))
