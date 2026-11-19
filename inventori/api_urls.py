from django.urls import path
from inventori import api_views

app_name = "api-inventori"
urlpatterns = [
    path("inventori/", api_views.bahan_list, name="bahan-list"),
    path("inventori/<uuid:bahan_id>/", api_views.bahan_detail, name="bahan-detail"),
]