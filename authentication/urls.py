from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path("", views.welcome, name="welcome"),
    path("login/", views.login_page,name="login"),
    path("register/", views.register_page, name="register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("logout/", views.logout_page, name="logout")
]