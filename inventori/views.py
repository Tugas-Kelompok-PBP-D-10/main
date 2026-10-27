from django.shortcuts import render, redirect, get_object_or_404
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
        })
    return JsonResponse(data, safe=False)

@login_required(login_url='/login/')
def show_inventori(request):
    context = {
        "inventori": request.user.inventori,
        "form": BahanForm(),
    }
    return render(request, "inventori.html", context)

@login_required(login_url='/login/')
def update_inventori(request):
    bahan2 = Bahan.objects.filter(inventory=request.user.inventori)
    
    BahanFormSet = modelformset_factory(Bahan, form=BahanForm, exclude=["inventory"], extra=0, can_delete=True)
    if request.method == 'POST':
        formset = BahanFormSet(request.POST, queryset=bahan2)
        if formset.is_valid():
            formset.save()
            return redirect("inventori")
        else:
            messages.error(request, "Gagal menyimpan: Pastikan stok tidak 0")
    else:
        formset = BahanFormSet(queryset=bahan2)
    context = {
        "formset": formset,
    }
    return render(request, "components/update_inventori.html", context)

@login_required(login_url='/login/')
def delete_bahan(request, bahan_id):
    bahan = get_object_or_404(Bahan, pk=bahan_id)

    if request.method == "POST":
        bahan.delete()
        messages.success(request, "Bahan berhasil dihapus!")
        return redirect("update_inventori")
    return redirect("update_inventori")

@login_required(login_url='/login/')
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
