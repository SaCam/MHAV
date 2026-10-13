def mhav_permissions(request):
    user = request.user
    if not user.is_authenticated or not user.is_active:
        return {
            'mhav_can_manage_users': False,
            'mhav_can_edit_website': False,
            'mhav_can_access_beheer': False,
        }
    is_admin = user.is_superuser or user.groups.filter(name='MHAV - Administrator').exists()
    # Editing is independent of trainer membership. Respect explicitly assigned
    # Django permissions, including other website/content editor permissions.
    can_edit_website = is_admin or any(user.has_perm(permission) for permission in (
        'website.change_homepagecontent',
        'website.change_sectionpagecontent',
        'website.change_websiteimage',
        'website.change_sitepage',
        'website.add_sitepage',
        'website.change_instructor',
        'content.change_newspost',
        'content.add_newspost',
    ))
    return {
        'mhav_can_manage_users': is_admin,
        'mhav_can_edit_website': can_edit_website,
        'mhav_can_access_beheer': is_admin or can_edit_website,
    }
