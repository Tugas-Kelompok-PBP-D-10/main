from django.core.management.base import BaseCommand, CommandError

from recipe.services import import_high_protein_spoonacular_recipes


class Command(BaseCommand):
    help = (
        "Impor resep Spoonacular baru dengan protein minimal 30 g per porsi. "
        "Resep yang sudah ada tidak ditimpa."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--query",
            required=True,
            help="Nama resep atau bahan pencarian (kata Indonesia umum dinormalisasi).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maksimal resep yang diminta dari API (1–50; default 10).",
        )

    def handle(self, *args, **options):
        result = import_high_protein_spoonacular_recipes(
            options["query"],
            limit=options["limit"],
        )
        if result.get("status") != "ok":
            raise CommandError(
                result.get("message") or f"Impor Spoonacular gagal ({result.get('status')})."
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Impor selesai: "
                f"{result['created']} resep baru, "
                f"{result['duplicates']} duplikat dilewati, "
                f"{result['skipped']} resep tidak memenuhi syarat."
            )
        )
