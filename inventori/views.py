from django.shortcuts import render
from .models import Bahan
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

# Create your views here.
def get_bahan_json(request):
    bahan2 = Bahan.objects.filter(inventory=request.user.inventori)
    data = []
    for bahan in bahan2:
        data.append({
            "nama": bahan.name,
            "stok": bahan.stock,
            "kandungan-protein": bahan.protein_content,
        })
    return JsonResponse(data, safe=False)

@login_required(login_url='/login/')
def show_inventori(request):
    context = {
        "inventori": request.user.inventori,
    }
    return render(request, "inventori.html", context)