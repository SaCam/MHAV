"""Curated MHAV access levels. Only trusted account managers may assign these."""
from django.contrib.auth.models import Group, Permission

ROLE_LABELS = {
    'MHAV - Lid': 'Lid',
    'MHAV - Trainer': 'Trainer',
    'MHAV - Websitebeheer': 'Website bewerken',
    'MHAV - Administrator': 'Administrator',
}
ROLE_PERMISSIONS = {
    'MHAV - Administrator': [],
    'MHAV - Lid': [],
    'MHAV - Trainer': [],  # Trainer-specific features will use group membership later.
    'MHAV - Websitebeheer': [
        ('website', 'change_homepagecontent'),
        ('website', 'change_sectionpagecontent'),
        ('website', 'change_websiteimage'),
        ('website', 'change_sitepage'),
        ('website', 'add_sitepage'),
        ('website', 'delete_sitepage'),
        ('website', 'change_instructor'),
        ('website', 'add_instructor'),
        ('website', 'delete_instructor'),
        ('content', 'add_newspost'),
        ('content', 'change_newspost'),
        ('content', 'delete_newspost'),
    ],
}

def ensure_roles():
    for name, codes in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=name)
        perms = []
        for app_label, codename in codes:
            permission = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if permission:
                perms.append(permission)
        group.permissions.set(perms)
