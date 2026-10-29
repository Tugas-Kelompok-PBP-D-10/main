from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.shortcuts import redirect
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/', include('allauth.urls')),

    path('voting/', include('voting.urls')),

    path('tracker/', include('tracker.urls')),
    # Ubah LoginView bawaan jadi redirect langsung ke tracker untuk testing lokal:
    path('accounts/login/', lambda request: redirect('/recipe/'), name='login'),
    path('', lambda request: redirect('/recipe/')),
    # Path untuk modul Inventori
    path('inventori/', include("inventori.urls")),
    # Path Recipe
    path('recipe/', include('recipe.urls')),
    path('', include('authentication.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
