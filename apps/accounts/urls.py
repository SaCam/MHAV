from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.urls import path
from . import views
from .forms import EmailLoginForm

app_name = "accounts"
urlpatterns = [
    path("registreren/", views.register, name="register"),
    path("inloggen/", auth_views.LoginView.as_view(template_name="registration/login.html", authentication_form=EmailLoginForm), name="login"),
    path("uitloggen/", auth_views.LogoutView.as_view(), name="logout"),
    path("mijn-mhav/", views.dashboard, name="dashboard"),
    path("profiel/", views.profile_edit, name="profile"),
    path("wachtwoord-wijzigen/", auth_views.PasswordChangeView.as_view(
        template_name="registration/password_change_form.html",
        success_url=reverse_lazy("accounts:password_change_done")), name="password_change"),
    path("wachtwoord-gewijzigd/", auth_views.PasswordChangeDoneView.as_view(
        template_name="registration/password_change_done.html"), name="password_change_done"),
    path("wachtwoord-vergeten/", auth_views.PasswordResetView.as_view(template_name="registration/password_reset_form.html", email_template_name="registration/password_reset_email.txt", subject_template_name="registration/password_reset_subject.txt", success_url="/account/wachtwoord-vergeten/verzonden/"), name="password_reset"),
    path("wachtwoord-vergeten/verzonden/", auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("wachtwoord-herstellen/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html", success_url="/account/wachtwoord-herstellen/gelukt/"), name="password_reset_confirm"),
    path("wachtwoord-herstellen/gelukt/", auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
]
urlpatterns += [
    path('trainer/profiel/', views.trainer_profile_edit, name='trainer_profile'),
    path('beheer/trainers/<int:user_id>/', views.beheer_trainer_profile, name='beheer_trainer_profile'),
    path('beheer/', views.beheer, name='beheer'),
    path('beheer/gebruikers/', views.beheer_users, name='beheer_users'),
    path('beheer/gebruikers/<int:user_id>/', views.beheer_user_edit, name='beheer_user_edit'),
]
