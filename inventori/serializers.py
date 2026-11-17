from django.utils.html import strip_tags
from rest_framework import serializers

from .models import Inventori, Bahan


class BahanSerializer(serializers.ModelSerializer):

    class Meta:
        model = Bahan
        fields = [
            "id", "name", "stock", "inventory",
        ]
        read_only_fields = ["id", "inventory"]

    def validate_name(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Nama tidak boleh kosong.")
        return value

    def validate_stock(self, value):
        if value <= 0:
            raise serializers.ValidationError("Stok harus lebih dari 0.")
        return value