# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Inventori

# Membuat objek Inventori baru saat pengguna mendaftar ke website
@receiver(post_save, sender=User)
def create_user_inventory(sender, instance, created, **kwargs):
    if created:
        Inventori.objects.create(user=instance)

# Menyimpan perubahan pada objek Inventori ketika objek User disimpan
@receiver(post_save, sender=User)
def save_user_inventory(sender, instance, **kwargs):
    instance.inventori.save()