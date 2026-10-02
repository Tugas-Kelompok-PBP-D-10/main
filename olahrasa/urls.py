from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/', include('allauth.urls')),

    path('tracker/', include('tracker.urls')),
    # Ubah LoginView bawaan jadi redirect langsung ke tracker untuk testing lokal:
    path('accounts/login/', lambda request: redirect('/tracker/'), name='login'),
    path('', lambda request: redirect('/tracker/')),
    # Path untuk modul Inventori
    path("", include("inventori.urls")),
    # Path Recipe
    path('recipe/', include('recipe.urls')),
]
    path('inventory/', include('inventori.urls')),

    path('', include('authentication.urls')),
]
