from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.tracker_view, name="tracker"),
    path("complete/",views.complete_cooking,name="complete_cooking"),
    path("api/dashboard/",views.tracker_dashboard_api,name="dashboard_api"),

]