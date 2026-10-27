from django.shortcuts import render
from django.http import HttpResponse

def recipe_home(request):
    return HttpResponse("<h1>Coming Soon!</h1>")

# Create your views here.
