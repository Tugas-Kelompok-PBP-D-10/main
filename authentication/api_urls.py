
from django.urls import path
from . import api_views

urlpatterns = [
    path("csrf/", api_views.csrf_api, name="api-csrf"),
    path("register/", api_views.register_api, name="api-register"),
    path("login/", api_views.login_api, name="api-login"),
    path("logout/", api_views.logout_api, name="api-logout"),
    path("profile/", api_views.profile_api, name="api-profile"),
]
