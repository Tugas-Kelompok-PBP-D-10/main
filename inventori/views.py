from django.shortcuts import render, redirect
from django.contrib import messages
from django.forms import modelformset_factory
from .models import Bahan
from .forms import BahanForm
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

# Create your views here.
def get_bahan_json(request):
    bahan2 = Bahan.objects.filter(inventory=request.user.inventori)
    data = []
    for bahan in bahan2:
        data.append({
            "id" : bahan.id,
            "nama": bahan.name,
            "stok": bahan.stock,
            "kandungan_protein": bahan.protein_content,
        })
    return JsonResponse(data, safe=False)

@login_required(login_url='/login/')
def show_inventori(request):
    BahanFormSet = modelformset_factory(Bahan, form=BahanForm, exclude=["inventory"], extra=0, can_delete=True)
    bahan2 = Bahan.objects.filter(inventory=request.user.inventori)
    if request.method == 'POST':
        formset = BahanFormSet(request.POST, queryset=bahan2)
        if formset.is_valid():
            formset.save()
            return redirect("inventori")
    formset = BahanFormSet(queryset=bahan2)
    context = {
        "inventori": request.user.inventori,
        "form": BahanForm(),
        "formset": formset,
    }
    return render(request, "inventori.html", context)

def add_bahan(request):
    form = BahanForm(request.POST)

    if form.is_valid():
        bahan = form.save(commit=False)
        bahan.inventory = request.user.inventori
        bahan.save()
        return JsonResponse(
            {"message": "Bahan berhasil ditambahkan.", "pk": str(bahan.id)},
            status=201,
        )

    return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
