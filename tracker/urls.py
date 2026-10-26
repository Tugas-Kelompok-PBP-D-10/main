from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.tracker_view, name="tracker"),
    path("complete/",views.complete_cooking,name="complete_cooking"),
    path("api/dashboard/",views.tracker_dashboard_api,name="dashboard_api"),
    path("api/history/",views.cooking_history_api,name="history_api"),
    path("api/nutrition-target/",views.nutrition_target_api,name="nutrition_target_api",),



]