from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Ingredient(models.Model):
    # Hubungkan ke User biar tiap user punya daftar bahan sendiri
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name