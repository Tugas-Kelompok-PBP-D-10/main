
from django.core.management.base import BaseCommand
from django.db import transaction

from tracker.models import Badge


class Command(BaseCommand):
    help = "Membuat achievement badges OlahRasa"

    @transaction.atomic
    def handle(self, *args, **options):

        badges = [
            {
                "code": "FIRST_COOK",
                "name": "First Cook",
                "description": "Berhasil memasak pertama kali!",
                "kind": Badge.Kind.TOTAL,
                "threshold": 1,
                "icon": " ",
            },
            {
                "code": "STREAK_3",
                "name": "Consistent Chef",
                "description": "Memasak selama 3 hari berturut-turut!",
                "kind": Badge.Kind.STREAK,
                "threshold": 3,
                "icon": " ",
            },
            {
                "code": "TOTAL_10",
                "name": "Master Chef",
                "description": "Berhasil memasak sebanyak 10 kali!",
                "kind": Badge.Kind.TOTAL,
                "threshold": 10,
                "icon": " ",
            },
        ]

        for data in badges:
            badge, created = Badge.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "kind": data["kind"],
                    "threshold": data["threshold"],
                    "icon": data["icon"],
                }
            )

            action = "Created" if created else "Updated"

            self.stdout.write(
                f"{action}: {badge.name}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Achievement badges berhasil disiapkan!"
            )
        )
