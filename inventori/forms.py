from django.forms import ModelForm, TextInput, NumberInput
from django.core.exceptions import ValidationError
from .models import Bahan

class BahanForm(ModelForm):
    class Meta:
        model = Bahan
        fields = [
            "name",
            "stock",
        ]

        labels = {
            "name": "Nama bahan",
            "stock": "Stok bahan",
        }

        widgets = {
            "name": TextInput(
                attrs={
                    "placeholder": "Nama bahan",
                    "maxlength": 255,
                    "style": 'width: 10rem !important;', # Memastikan lebar form 10rem
                    "class": "form-box", # Untuk menautkan pengaturan css lain
                }
            ),
            "stock": NumberInput(
                attrs={
                    "placeholder": "Unit",
                    "min": 1,
                    "style": 'width: 5rem !important;', # Memastikan lebar form 5rem
                    "class": "form-box", # Untuk menautkan pengaturan css lain
                }
            ),
        }

    # Fungsi untuk memastikan stok pada form yang di-submit tidak nol.
    def clean_stock(self):
        stok = self.cleaned_data.get('stock')
        if stok is not None and stok <= 0:
            raise ValidationError("Stok tidak boleh 0.")
        return stok