from django.urls import path
from . import views
app_name='planning'
urlpatterns=[
    path('',views.overview,name='overview'),
    path('instructeur/seizoenen/', views.trainer_seasons, name='trainer_seasons'),
    path('instructeur/seizoen/<int:pk>/beschikbaarheid/', views.trainer_availability, name='trainer_availability'),
    path('aanmeldingen/', views.application_list, name='application_list'),
    path('aanmeldingen/<int:pk>/', views.application_detail, name='application_detail'),
    path('cursusaanbod/', views.catalogue, name='catalogue'),
    path('seizoen/<int:pk>/cursussen/', views.season_course_offerings, name='season_course_offerings'),
    path('seizoen/<int:pk>/',views.season_detail,name='season_detail'),
    path('lesgroep/<int:pk>/',views.group_detail,name='group_detail'),
    path('lesgroep/<int:pk>/les/<str:lesson_date>/instructeur/', views.lesson_instructor_override, name='lesson_instructor_override'),
    path('seizoen/<int:season_pk>/lesgroep/nieuw/', views.group_manage, name='group_new'),
    path('lesgroep/<int:pk>/bewerken/', views.group_manage, name='group_edit'),
    path('overzicht/<slug:kind>/',views.records,name='records'),
    path('nieuw/<slug:kind>/',views.edit,name='new'),
    path('bewerken/<slug:kind>/<int:pk>/',views.edit,name='edit'),
]
