from django.shortcuts import render

# Create your views here.
def show_inventori(request):
    return render(request, "inventori.html")