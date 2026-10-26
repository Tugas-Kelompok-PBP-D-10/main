import uuid
from django.conf import settings
from django.db import models

# Create your models here.
class Inventori(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventori")

    @property
    def is_empty(self):
        return not self.bahans.exist()

class Bahan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    stock = models.PositiveIntegerField()
    inventory = models.ForeignKey(Inventori, on_delete=models.CASCADE, related_name="bahans", default=None)

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock > 0




