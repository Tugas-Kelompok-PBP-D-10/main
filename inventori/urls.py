from django.contrib import admin
from django.urls import path
from inventori.views import *

urlpatterns = [
    path('', show_inventori, name="inventori"),
    path('api/bahan/', get_bahan_json, name="get_bahan_json"),
    path('add-ajax/', add_bahan, name="add_bahan"),
    path('update/', update_inventori, name="update_inventori"),
    path('<uuid:bahan_id>/delete/', delete_bahan, name="delete_bahan"),
]