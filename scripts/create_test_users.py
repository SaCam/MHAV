"""Create deterministic, local-only MHAV test users.

Run from the project root:
    python manage.py shell < scripts/create_test_users.py
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

if not settings.DEBUG:
    raise RuntimeError("Refusing to create test users unless DEBUG=True (local development only).")

User = get_user_model()
first_names = [
    "Thomas", "Emma", "Sophie", "Daan", "Lisa", "Bram", "Julia", "Max", "Noor", "Tim",
    "Eva", "Lars", "Fleur", "Jesse", "Anna", "Milan", "Lotte", "Finn", "Sara", "Ruben",
    "Nina", "Luuk", "Tessa", "Sem", "Roos",
]
last_names = [
    "van Dijk", "Jansen", "de Vries", "Bakker", "Visser", "Smit",
    "Meijer", "Bos", "Mulder", "van den Berg", "Peters",
]

required_groups = ("MHAV - Lid", "MHAV - Trainer", "MHAV - Websitebeheer")
groups = {name: Group.objects.get(name=name) for name in required_groups}

created = 0
skipped = 0
with transaction.atomic():
    for i, first_name in enumerate(first_names, start=1):
        email = f"testuser{i:02d}@example.com"
        if User.objects.filter(email__iexact=email).exists():
            skipped += 1
            continue
        user = User.objects.create_user(
            username=f"mhav_test_{i:02d}",
            email=email,
            password="TestMHAV2026!",
            first_name=first_name,
            last_name=last_names[(i - 1) % len(last_names)],
            is_active=True,
        )
        if i <= 20:
            user.groups.add(groups["MHAV - Lid"])
        if i <= 5:
            user.groups.add(groups["MHAV - Trainer"])
        if i in (6, 7):
            user.groups.add(groups["MHAV - Websitebeheer"])
        created += 1

print(f"Created {created} test users; skipped {skipped} existing users.")
print("Example login: testuser01@example.com / TestMHAV2026!")
