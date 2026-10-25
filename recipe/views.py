from django.shortcuts import render
from .models import Ingredient, Recipe  # 1. Pastikan Recipe di-import

def recipe_home(request):
    if request.method == 'POST':
        ingredient_name = request.POST.get('ingredient_name')
        quantity = request.POST.get('quantity', '')
        
        # Simpan bahan jika input tidak kosong
        if ingredient_name and ingredient_name.strip():
            raw_ingredients = ingredient_name.split(',')
            
            for item in raw_ingredients:
                clean_name = item.strip()
                if clean_name:
                    if request.user.is_authenticated:
                        Ingredient.objects.create(
                            user=request.user, 
                            name=clean_name,
                            quantity=quantity.strip()
                        )
                    else:
                        Ingredient.objects.create(
                            name=clean_name,
                            quantity=quantity.strip()
                        )

    # Ambil daftar bahan tersimpan
    if request.user.is_authenticated:
        saved_ingredients = Ingredient.objects.filter(user=request.user).order_by('-created_at')
    else:
        saved_ingredients = Ingredient.objects.filter(user=None).order_by('-created_at')

    # 2. AMBIL SEMUA DATA RESEP DARI DATABASE (Tadi bagian ini hilang!)
    recipes = Recipe.objects.all()

    # 3. KIRIM 'recipes' KE CONTEXT
    context = {
        'ingredients': saved_ingredients,
        'recipes': recipes,
    }
    return render(request, 'recipe/recipe.html', context)