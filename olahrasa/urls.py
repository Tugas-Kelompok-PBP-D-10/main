from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/', include('allauth.urls')),

    path('tracker/', include('tracker.urls')),
    path('inventory/', include('inventori.urls')),

    path('', include('authentication.urls')),
]