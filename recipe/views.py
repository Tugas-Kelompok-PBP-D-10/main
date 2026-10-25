from django.shortcuts import render
from .models import Ingredient

def recipe_home(request):
    if request.method == 'POST':
        ingredient_name = request.POST.get('ingredient_name')
        
        # Simpan bahan jika input tidak kosong
        if ingredient_name and ingredient_name.strip():
            if request.user.is_authenticated:
                Ingredient.objects.create(user=request.user, name=ingredient_name.strip())
            else:
                Ingredient.objects.create(name=ingredient_name.strip())

    # Ambil daftar bahan tersimpan
    if request.user.is_authenticated:
        saved_ingredients = Ingredient.objects.filter(user=request.user).order_by('-created_at')
    else:
        saved_ingredients = Ingredient.objects.filter(user=None).order_by('-created_at')

    context = {
        'ingredients': saved_ingredients,
    }
    return render(request, 'recipe/recipe.html', context)