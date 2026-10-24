from django.forms import ModelForm, TextInput, NumberInput
from django.core.exceptions import ValidationError
from .models import Bahan

class BahanForm(ModelForm):
    class Meta:
        model = Bahan
        fields = [
            "name",
            "stock",
            "protein_content",
        ]

        labels = {
            "name": "Nama bahan",
            "stock": "Stok bahan",
            "protein_content": "Kandungan protein"
        }

        widgets = {
            "name": TextInput(
                attrs={
                    "placeholder": "nama bahan",
                    "maxlength": 255,
                    "style": 'width: 10rem !important;',
                    "class": "form-box",
                }
            ),
            "stock": NumberInput(
                attrs={
                    "min": 1,
                    "style": 'width: 5rem !important;',
                    "class": "form-box",
                }
            ),
            "protein_content": NumberInput(
                attrs={
                    "style": 'width: 5rem !important;',
                    "class": "form-box",
                }
            ),
        }

    def clean_stock(self):
        stok = self.cleaned_data.get('stock')
        if stok is not None and stok <= 0:
            raise ValidationError("Stok tidak boleh 0.")
        return stok