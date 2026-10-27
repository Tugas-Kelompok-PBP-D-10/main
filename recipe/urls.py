from django.urls import path
from . import views

app_name = 'recipe'

urlpatterns = [
    path('', views.recipe_home, name='home'),
]