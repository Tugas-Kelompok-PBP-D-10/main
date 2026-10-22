from django.contrib import admin
from django.urls import path
from inventori.views import *

urlpatterns = [
    path('', show_inventori, name="inventori"),
    path('api/bahan/', get_bahan_json, name="get_bahan_json"),
]