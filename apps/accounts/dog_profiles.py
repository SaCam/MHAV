from apps.planning.models import Dog, Combination

def ensure_application_dog(application):
    """Create a dog profile only for an application tied to a verified logged-in owner."""
    if not application.user_id:
        return None
    if application.linked_combination_id:
        dog = application.linked_combination.dog
        if application.linked_combination.handler_id != application.user_id:
            return None
    elif application.dog_profile_id:
        dog = application.dog_profile
    else:
        dog = Dog.objects.create(name=application.dog_name, breed=application.dog_breed, date_of_birth=application.dog_birth_date, notes=application.dog_notes)
    Combination.objects.get_or_create(handler_id=application.user_id, dog=dog)
    if application.dog_profile_id != dog.pk:
        application.dog_profile = dog
        application.save(update_fields=['dog_profile'])
    return dog
