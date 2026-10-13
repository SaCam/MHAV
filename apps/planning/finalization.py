"""Resolve intake records safely when an approved draft becomes a real enrollment."""
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Dog, Combination, Enrollment


def resolve_identity(app, *, create=False):
    User = get_user_model()
    email = app.email.strip().lower()
    if not email:
        return None, None, None, 'E-mailadres ontbreekt'
    matches = list(User.objects.filter(email__iexact=email)[:2])
    if len(matches) > 1:
        return None, None, None, 'Meerdere accounts met hetzelfde e-mailadres'
    user = matches[0] if matches else None
    if app.user_id and user and app.user_id != user.pk:
        return None, None, None, 'Aanvraag is aan een ander account gekoppeld'
    if app.user_id and not user:
        return None, None, None, 'Accountkoppeling en e-mailadres komen niet overeen'
    if user and (user.first_name and user.first_name.casefold().strip() != app.first_name.casefold().strip() or user.last_name and user.last_name.casefold().strip() != app.last_name.casefold().strip()):
        return None, None, None, 'Naam wijkt af van bestaand account; controleer identiteit'
    if not user and create:
        user = User(username='mhav_'+uuid4().hex[:24], email=email, first_name=app.first_name, last_name=app.last_name)
        user.set_unusable_password()
        user.save()
    if not app.dog_name.strip():
        return user, None, None, 'Naam hond ontbreekt'
    dog = None
    combo = None
    if app.linked_combination_id:
        combo = app.linked_combination
        if user and combo.handler_id != user.pk:
            return user, None, None, 'Gekoppelde combinatie hoort bij ander account'
        dog = combo.dog
    elif user:
        candidates = list(Combination.objects.filter(handler=user, dog__name__iexact=app.dog_name.strip()).select_related('dog'))
        if app.dog_birth_date:
            candidates = [c for c in candidates if c.dog.date_of_birth == app.dog_birth_date]
        if app.dog_breed.strip():
            candidates = [c for c in candidates if not c.dog.breed or c.dog.breed.casefold().strip() == app.dog_breed.casefold().strip()]
        if len(candidates)>1:
            return user,None,None,'Meerdere mogelijke honden; handmatige controle nodig'
        if candidates:
            combo=candidates[0];dog=combo.dog
        else:
            same_name=list(Combination.objects.filter(handler=user,dog__name__iexact=app.dog_name.strip()).select_related('dog'))
            if same_name and (not app.dog_birth_date or any(c.dog.date_of_birth is None for c in same_name)):
                return user,None,None,'Hond met dezelfde naam en onvoldoende identificatie; controleer handmatig'
    if not dog and create:
        dog=Dog.objects.create(name=app.dog_name.strip(),breed=app.dog_breed.strip(),date_of_birth=app.dog_birth_date,notes=app.dog_notes)
    if dog and user and not combo and create:
        combo,_=Combination.objects.get_or_create(handler=user,dog=dog)
    return user,dog,combo,None


def inspect_application(app, group):
    if app.status == app.Status.REJECTED:
        return 'Aanvraag is afgewezen'
    if not group.planning_locked_at:
        return 'Lesgroep is niet goedgekeurd'
    user,dog,combo,problem=resolve_identity(app,create=False)
    if problem:return problem
    if combo and Enrollment.objects.filter(group=group,combination=combo).exists():
        return 'Deze combinatie heeft al een inschrijving in deze lesgroep'
    # Do not block a planned capacity exception; its authorization was recorded at placement time.
    return None
