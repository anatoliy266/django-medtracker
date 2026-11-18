from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    # HTML-страницы авторизации
    path("login/", auth_views.LoginView.as_view(
        template_name="accounts/login.html",
        redirect_authenticated_user=True
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(
        next_page='accounts:login'
    ), name="logout"),
    path("signup/", views.signup, name="signup"),

    # REST API авторизации
    path("api/signup/", views.api_signup, name="api-signup"),
    path("api/login/", views.api_login, name="api-login"),
    path("api/logout/", views.api_logout, name="api-logout"),
]