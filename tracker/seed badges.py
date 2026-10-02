from django.core.management.base import BaseCommand

from tracker.models import Badge

BADGES = [
    ("first-cook", "First Cook", "Selesaikan masakan pertamamu", "total", 1),
    ("streak-3", "3-Day Streak", "Masak 3 hari berturut-turut", "streak", 3),
    ("streak-7", "Weekly Warrior", "Masak 7 hari berturut-turut", "streak", 7),
    ("streak-30", "Kitchen Legend", "Masak 30 hari berturut-turut", "streak", 30),
    ("cook-10", "Home Chef", "Selesaikan 10 masakan", "total", 10),
    ("cook-50", "Waste Fighter", "Selesaikan 50 masakan", "total", 50),
]


class Command(BaseCommand):
    help = "Mengisi data badge awal"

    def handle(self, *args, **options):
        for code, name, desc, kind, threshold in BADGES:
            Badge.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": desc, "kind": kind, "threshold": threshold},
            )
        self.stdout.write(self.style.SUCCESS(f"{len(BADGES)} badge siap."))