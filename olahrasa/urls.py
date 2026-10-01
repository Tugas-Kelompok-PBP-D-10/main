from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tracker/', include('tracker.urls')),
    # Ubah LoginView bawaan jadi redirect langsung ke tracker untuk testing lokal:
    path('accounts/login/', lambda request: redirect('/tracker/'), name='login'),
    path('', lambda request: redirect('/tracker/')),
]