from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("account/", include("apps.accounts.urls")),
    path("nieuws/", include("apps.content.urls")),
    path("account/beheer/cursusadministratie/", include("apps.planning.urls")),
    path("", include("apps.website.urls")),
]
if settings.DEBUG:
    from apps.planning.dev_mailbox import mailbox
    urlpatterns += [path('dev/test-emailbox/', mailbox, name='dev_mailbox')]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
