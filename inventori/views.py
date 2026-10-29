from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.forms import modelformset_factory
from django.db.models import Count
from .models import Bahan
from .forms import BahanForm
from django.http import JsonResponse
import json
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from recipe.views import _voting_routes_available, _login_url
from recipe.models import RecipeInteraction, Recipe, RecipeCookingEvent
from recipe.services import get_recipe_image_url
from recipe.views import spoonacular_recipe_search_api

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
        "recipe_login_url": _login_url(request),
        "voting_routes_available": _voting_routes_available(),
    }
    return render(request, "inventori.html", context)

@require_GET
def inventory_recipe_search_api(request):
    response = spoonacular_recipe_search_api(request)

    if response.status_code != 200:
        return response

    data = json.loads(response.content.decode("utf-8"))
    recipes = data.get("results", [])
    # recipe_ids = [r["pk"] for r in recipes if "pk" in r]

    # statuses = {}
    # cooking_counts = {}

    # if request.user.is_authenticated and recipe_ids:
    #     statuses = {
    #         row["recipe_id"]: row
    #         for row in RecipeInteraction.objects.filter(
    #             user=request.user,
    #             recipe_id__in=recipe_ids,
    #         ).values("recipe_id", "viewed_at", "completed_at")
    #     }

    #     cooking_counts = dict(
    #         RecipeCookingEvent.objects.filter(
    #             user=request.user,
    #             recipe_id__in=recipe_ids,
    #         )
    #         .values("recipe_id")
    #         .annotate(total=Count("pk"))
    #         .values_list("recipe_id", "total")
    #     )

    #     for recipe_id, status in statuses.items():
    #         if status.get("completed_at"):
    #             cooking_counts[recipe_id] = max(1, cooking_counts.get(recipe_id, 0))

    for recipe in recipes:
        # r_id = recipe.get("pk")
        # status = statuses.get(r_id, {})
        # c_count = cooking_counts.get(r_id, 0)

        # recipe["interaction_viewed"] = bool(status.get("viewed_at"))
        # recipe["cooking_count"] = c_count
        # recipe["interaction_completed"] = c_count > 0 or bool(status.get("completed_at"))
        recipe["card_image_url"] = recipe.get("image") or recipe.get("image_url", "")

    return JsonResponse(data)

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
            messages.error(request, "Gagal menyimpan perubahan. Pastikan stok tidak kurang dari 1.")
    
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
