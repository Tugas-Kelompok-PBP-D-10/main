from django.urls import path,include
from . import views

app_name = 'recipe'

urlpatterns = [
    path('', views.recipe_home, name='home'),
]