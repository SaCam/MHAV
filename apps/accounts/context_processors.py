def mhav_permissions(request):
    user = request.user
    return {'mhav_can_manage_users': (user.is_authenticated and user.is_active and (user.is_superuser or user.groups.filter(name='MHAV - Administrator').exists()))}
