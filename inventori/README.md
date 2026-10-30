## Daftar Isi
[1. Penjelasan singkat modul inventori](#modul-inventori)

[2. Penggunaan Kode dari Tutorial](#penggunaan-kode-dari-tutorial)

[3. AI Disclosure](#ai-disclosure)

# Modul Inventori
Modul ini dikerjakan oleh Velicia Willy - 2506657384

### Fitur-Fitur pada Modul Ini
1. Menyimpan daftar bahan makanan yang dimiliki pengguna.
2. Menyimpan informasi nama dan stok untuk setiap bahan yang dimiliki pengguna.
3. Menambahkan bahan ke inventori.
4. Mengedit inventori (menghapus bahan serta mengedit nama dan stok bahan).
5. Menampilkan rekomendasi resep berdasarkan bahan-bahan yang ada pada inventori.


# Penggunaan Kode dari Tutorial
Beberapa potongan kode saya ambil langsung dari Tutorial yang terdapat pada web PBP, kemudian saya adaptasi agar sesuai dengan kebutuhan modul saya. Berikut kode yang saya ambil dari Tutorial:

1. getCookie() dalam tag ```<script>``` dalam ```inventori.html```
2. buildBahanRow() dalam tag ```<script>``` dalam ```inventori.html```
3. fetchBahan() dalam tag ```<script>``` dalam ```inventori.html```
4. addBahan() dalam tag ```<script>``` dalam ```inventori.html```
5. Popup ```tambah_bahan_modal.html```

# AI Disclosure
Saya berdiskusi dengan Gemini AI ketika mengalami kesulitan atau menemukan eror. Saya memulai diskusi dengan memaparkan eror yang saya alami (pesan eror yang muncul jika ada, atau bagian yang tidak berfungsi sesuai ekspektasi saya), kemudian saya memaparkan usaha yang sudah saya lakukan tapi tidak berhasil untuk mengatasi masalah tersebut, lalu saya meminta solusi dari AI atas masalah tersebut.

Saya menggunakan Gemini AI untuk men-generate kode pada beberapa bagian modul saya. Akan tetapi, saya tidak memberikan AI source code dari website saya. Oleh karena itu, kode yang di-generate oleh AI masih perlu dibaca dan dimodifikasi secara manual agar tidak menimbulkan masalah dan dapat bekerja pada source code saya. Berikut penggunaannya.

### Menghubungkan model Inventori dengan model User
Prompt exact: "I have a django model called Inventory. When a user signs in for the first time on my website, my website should automatically create a new Inventory object for that user. And when the user signs out and signs in again, the Inventory object that was made was shown again. How can I do that?"

Kode yang saya terima dari AI dan aplikasikan sesuai kebutuhan:
```
# models.py
from django.db import models
from django.contrib.auth.models import User

class Inventory(models.Model):
    # Link the inventory to the user
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='inventory')
    
    # Your other inventory fields here
    items_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username}'s Inventory"

# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Inventory

# Creates the inventory when a new user is created
@receiver(post_save, sender=User)
def create_user_inventory(sender, instance, created, **kwargs):
    if created:
        Inventory.objects.create(user=instance)

# Saves the inventory whenever the user object gets saved
@receiver(post_save, sender=User)
def save_user_inventory(sender, instance, **kwargs):
    instance.inventory.save()

# apps.py
from django.apps import AppConfig

class YourAppNameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'your_app_name' # replace with your actual app name

    def ready(self):
        # Import the signals file here
        import your_app_name.signals
```

### Membuat validasi pada form untuk mencegah stok <= 0
Prompt exact: "I'm using a NumberInput in a django form. I want to make sure that users can't submit the form if the NumberInput field has a value of 0 or less. How do I do that?"

Kode yang saya terima dari AI dan aplikasikan sesuai kebutuhan:
```
from django import forms

class InventoryForm(forms.Form):
    # Set min_value to 1 (or 0.01 if using DecimalField)
    quantity = forms.IntegerField(
        min_value=1, 
        widget=forms.NumberInput()
    )
```
```
from django import forms
from django.core.exceptions import ValidationError

class ItemForm(forms.ModelForm):
    # ... Meta class here ...

    def clean_quantity(self):
        # Get the value submitted by the user
        qty = self.cleaned_data.get('quantity')

        # Check if it is 0 or less
        if qty is not None and qty <= 0:
            raise ValidationError("You must add at least 1 item!")

        return qty
```

### Men-justify Popup Tambah Bahan ke Tengah Halaman
Prompt exact: "How to align a popup to the center of the page?"

CSS yang saya terima dari AI dan aplikasikan sesuai kebutuhan:
```
.popup-overlay {
  position: fixed; /* Locks to the screen viewport */
  top: 0; 
  left: 0;
  width: 100vw; 
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.5); /* Dark semi-transparent background */
  z-index: 1000; /* Ensures it sits on top of everything else */
  
  /* Use Grid to center the inner box perfectly */
  display: grid;
  place-items: center; 
}

.popup-box {
  background: white;
  padding: 24px;
  /* Width and height are controlled automatically or defined here */
}
```

### Melakukan Bulk-Update Bahan dalam Inventori
Prompt exact: "I have an inventory with multiple items in it. How do I update all those items at once?"

Kode yang saya terima dari AI dan aplikasikan sesuai kebutuhan:
```
from django.shortcuts import render, redirect
from django.forms import modelformset_factory
from django.contrib.auth.decorators import login_required
from .models import Item

@login_required
def bulk_update_view(request):
    # Create the formset factory, specifying which fields to allow editing. 
    # extra=0 prevents it from generating blank forms for creating new items.
    ItemFormSet = modelformset_factory(Item, fields=('quantity',), extra=0)
    
    # Securely fetch only the current user's items
    user_items = Item.objects.filter(inventory=request.user.inventori)

    if request.method == 'POST':
        formset = ItemFormSet(request.POST, queryset=user_items)
        if formset.is_valid():
            formset.save()
            return redirect('inventory_list') # Redirect after successful save
    else:
        formset = ItemFormSet(queryset=user_items)

    return render(request, 'bulk_update.html', {'formset': formset})
```
```
<form method="POST" action="">
    {% csrf_token %}
    
    <!-- REQUIRED for formsets to work -->
    {{ formset.management_form }}
    
    <div class="my-items-grid">
        {% for form in formset %}
            <div class="item-row">
                <!-- REQUIRED: Renders a hidden input with the item's database ID -->
                {{ form.id }} 
                
                <!-- Display the item's name (read-only) and the editable quantity field -->
                <span>{{ form.instance.name }}</span>
                {{ form.quantity }}
            </div>
        {% endfor %}
    </div>
    
    <button type="submit">Update All Quantities</button>
</form>
```

### Melakukan Delete Bahan Tanpa Men-submit Form Update Inventori
Prompt exact: "I have a form that has a delete form inside it. Is it possible to submit the delete form only, without submitting the outer form too?"

Kode yang saya terima dari AI dan aplikasikan sesuai kebutuhan:
```
<!-- MAIN FORM -->
<form method="post" id="bahan-form" action="{% url 'inventori' %}">
    {% csrf_token %}
    {{ formset.management_form }} 

    {% for form in formset %}
        <div class="bahan-form">
            {{ form.id }}
            
            <!-- This button links to the external delete form using its ID -->
            <button type="submit" 
                    form="delete-form-{{ form.instance.id }}" 
                    class="edit"
                    onclick="return confirm('Apakah Anda yakin ingin menghapus bahan ini?');">
                -
            </button>
            
            {{ form.name }}
            {{ form.stock }} 
            {{ form.protein_content }}
        </div>
    {% endfor %}
    
    <button id="save-button" type="submit" class="button">Simpan Perubahan</button>
</form>

<!-- HIDDEN DELETE FORMS (Placed completely outside the main form) -->
{% for form in formset %}
    <form id="delete-form-{{ form.instance.id }}" 
          method="post" 
          action="{% url 'delete_bahan' form.instance.id %}" 
          style="display: none;">
        {% csrf_token %}
    </form>
{% endfor %}
```

### Mem-blur Halaman di Belakang Popup
Prompt exact: "How do I blur the rest of the page when the popup is open?"

CSS yang saya terima dari AI dan aplikasikan sesuai kebutuhan:
```
<!-- The new backdrop -->
<div class="blur-backdrop" id="backdrop"></div>

<!-- Your existing popup -->
<div class="popup" id="popup">
    Your content here
</div>
```
```
.blur-backdrop {
  position: fixed;
  inset: 0; /* Covers the entire screen */
  background: rgba(0, 0, 0, 0.3); /* Optional: darkens the background slightly */
  backdrop-filter: blur(5px); /* Blurs whatever is behind it */
  -webkit-backdrop-filter: blur(5px); /* Safari support */
  z-index: 999; /* Places it just below the popup */
}

.popup {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000; /* Keeps the popup above the blurred backdrop */
}
```

### Fungsi views untuk mem-fetch resep
Prompt exact: "My teammate has already implemented a search function. How can I use it in my views.py? And how would calling this function on JavaScript look like?" 
Selain itu, saya juga memberikan fungsi-fungsi views serta services dari modul Recipe yang relevan.

Kode yang saya terima dari AI dan aplikasikan sesuai kebutuhan:
```
# inventory/views.py
import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Count

# 1. Import your teammate's view function directly
from recipe_app.views import spoonacular_recipe_search_api 
from .models import RecipeInteraction, RecipeCookingEvent

@require_GET
def inventory_recipe_search_api(request):
    # 2. Call their view function using the incoming request
    teammate_response = spoonacular_recipe_search_api(request)

    # 3. If their view returned an error (e.g., 400 or 503), pass it straight to the browser
    if teammate_response.status_code != 200:
        return teammate_response

    # 4. Extract and decode the JSON dictionary from their response
    data = json.loads(teammate_response.content.decode("utf-8"))
    recipes = data.get("results", [])
    recipe_ids = [r["id"] for r in recipes if "id" in r]

    # 5. Fetch user interaction stats for these recipes
    statuses = {}
    cooking_counts = {}

    if request.user.is_authenticated and recipe_ids:
        statuses = {
            row["recipe_id"]: row
            for row in RecipeInteraction.objects.filter(
                user=request.user,
                recipe_id__in=recipe_ids,
            ).values("recipe_id", "viewed_at", "completed_at")
        }

        cooking_counts = dict(
            RecipeCookingEvent.objects.filter(
                user=request.user,
                recipe_id__in=recipe_ids,
            )
            .values("recipe_id")
            .annotate(total=Count("pk"))
            .values_list("recipe_id", "total")
        )

        for recipe_id, status in statuses.items():
            if status.get("completed_at"):
                cooking_counts[recipe_id] = max(1, cooking_counts.get(recipe_id, 0))

    # 6. Attach your custom attributes to each item in the results array
    for recipe in recipes:
        r_id = recipe.get("id")
        status = statuses.get(r_id, {})
        c_count = cooking_counts.get(r_id, 0)

        recipe["interaction_viewed"] = bool(status.get("viewed_at"))
        recipe["cooking_count"] = c_count
        recipe["interaction_completed"] = c_count > 0 or bool(status.get("completed_at"))
        recipe["card_image_url"] = recipe.get("image") or recipe.get("image_url", "")

    # 7. Return the enriched JSON to JavaScript
    return JsonResponse(data)
```
```
async function searchInventoryRecipes() {
    const recipeGrid = document.getElementById('recipe-grid');
    
    // 1. Gather inventory items from DOM
    const inventoryItems = Array.from(document.querySelectorAll('.inventory-item-name'))
        .map(el => el.textContent.trim())
        .filter(Boolean);

    if (inventoryItems.length === 0) {
        recipeGrid.innerHTML = '<p>Tidak ada bahan di inventori.</p>';
        return;
    }

    const query = inventoryItems.join(',');

    try {
        // 2. Fetch enriched data from your wrapper endpoint
        const response = await fetch(`${INVENTORY_SEARCH_URL}?q=${encodeURIComponent(query)}`);
        
        if (!response.ok) throw new Error('Gagal mengambil resep');

        const data = await response.json();
        recipeGrid.innerHTML = ''; // Clear previous content

        // 3. Check data.results array
        if (data.results && data.results.length > 0) {
            data.results.forEach(resep => {
                // Pass each enriched recipe object to buildResepCard
                recipeGrid.appendChild(buildResepCard(resep));
            });
        } else {
            recipeGrid.innerHTML = '<p>Tidak ada resep yang cocok ditemukan.</p>';
        }

    } catch (error) {
        console.error('Error fetching recipes:', error);
        recipeGrid.innerHTML = '<p>Terjadi kesalahan saat memuat resep.</p>';
    }
}
```