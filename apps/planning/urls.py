from django.urls import path
from . import views
app_name='planning'
urlpatterns=[
    path('',views.overview,name='overview'),
    path('cursusaanbod/', views.catalogue, name='catalogue'),
    path('seizoen/<int:pk>/',views.season_detail,name='season_detail'),
    path('lesgroep/<int:pk>/',views.group_detail,name='group_detail'),
    path('overzicht/<slug:kind>/',views.records,name='records'),
    path('nieuw/<slug:kind>/',views.edit,name='new'),
    path('bewerken/<slug:kind>/<int:pk>/',views.edit,name='edit'),
]
