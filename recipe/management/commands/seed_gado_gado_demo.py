from django.core.management.base import BaseCommand
from django.db import transaction

from recipe.models import Recipe


DEMO_TITLE = "Gado-Gado"


class Command(BaseCommand):
    help = "Menambahkan satu demo Gado-Gado tanpa mengubah resep yang sudah ada."

    def handle(self, *args, **options):
        with transaction.atomic():
            existing = (
                Recipe.objects.select_for_update()
                .filter(title__iexact=DEMO_TITLE)
                .order_by("pk")
                .first()
            )
            if existing:
                self.stdout.write(
                    self.style.WARNING(
                        f"Demo tidak dibuat: resep {DEMO_TITLE} sudah ada "
                        f"(ID {existing.pk}); datanya tidak diubah."
                    )
                )
                return

            recipe = Recipe.objects.create(
                title=DEMO_TITLE,
                description=(
                    "Gado-Gado sayuran dengan kentang, tahu, tempe, dan telur, "
                    "disajikan bersama saus kacang yang dibuat sendiri. "
                    "Resep demo lokal ini melayani empat porsi."
                ),
                preparation_time=25,
                cooking_time=25,
                servings=4,
                source_type="local",
                source_name="Demo lokal OlahRasa",
                is_published=True,
                ingredients=[
                    {"name": "kentang", "amount": 400, "unit": "g"},
                    {"name": "kacang panjang", "amount": 150, "unit": "g"},
                    {"name": "tauge", "amount": 150, "unit": "g"},
                    {"name": "kol", "amount": 200, "unit": "g"},
                    {"name": "tahu putih", "amount": 200, "unit": "g"},
                    {"name": "tempe", "amount": 200, "unit": "g"},
                    {"name": "telur", "amount": 4, "unit": "butir"},
                    {"name": "kacang tanah", "amount": 200, "unit": "g"},
                    {"name": "bawang putih", "amount": 3, "unit": "siung"},
                    {"name": "cabai merah keriting", "amount": 2, "unit": "buah"},
                    {"name": "gula merah", "amount": 35, "unit": "g"},
                    {"name": "air asam jawa", "amount": 1, "unit": "sdm"},
                    {"name": "air hangat", "amount": 250, "unit": "ml"},
                    {"name": "garam", "amount": 0.5, "unit": "sdt"},
                    {
                        "name": "minyak goreng",
                        "original": "Minyak goreng secukupnya untuk menggoreng.",
                    },
                    {
                        "name": "emping",
                        "original": "Emping secukupnya untuk pelengkap.",
                    },
                ],
                instructions=(
                    "Cuci kentang, kacang panjang, tauge, dan kol. Rebus kentang "
                    "beserta telur hingga matang; angkat dan tiriskan.\n"
                    "Potong kacang panjang dan kol. Rebus atau kukus sebentar "
                    "kacang panjang, tauge, dan kol sampai matang tetapi masih "
                    "renyah, lalu tiriskan.\n"
                    "Potong tahu dan tempe, kemudian goreng sampai bagian luar "
                    "berwarna keemasan. Tiriskan dan potong sesuai selera.\n"
                    "Sangrai atau goreng kacang tanah dengan api kecil sampai "
                    "matang. Angkat dan dinginkan; goreng bawang putih serta "
                    "cabai sebentar.\n"
                    "Haluskan kacang tanah, bawang putih, cabai, gula merah, dan "
                    "garam hingga menjadi saus kacang.\n"
                    "Tambahkan air asam jawa dan air hangat sedikit demi sedikit "
                    "sambil diaduk sampai saus cukup kental untuk disiram. Cicipi "
                    "dan sesuaikan rasa; jangan menambahkan bahan yang belum "
                    "tercantum dalam resep.\n"
                    "Kupas dan belah telur. Potong kentang, tahu, dan tempe; tata "
                    "bersama sayuran di piring.\n"
                    "Siram dengan saus kacang dan sajikan dengan emping."
                ),
                nutrition_basis="unknown",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo {DEMO_TITLE} dibuat dengan ID {recipe.pk}. "
                "Foto dan nutrisi belum diisi."
            )
        )
