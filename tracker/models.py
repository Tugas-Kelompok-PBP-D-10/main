from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class CookingLog(models.Model):
    """Satu kali aktivitas memasak. Dipakai untuk streak dan akumulasi nutrisi."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cooking_logs")
    recipe_name = models.CharField(max_length=150, blank=True)
    cooked_on = models.DateField(default=timezone.localdate, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # nilai nutrisi hasil masakan ini
    protein_g = models.PositiveIntegerField(default=0)
    carbs_g = models.PositiveIntegerField(default=0)
    fat_g = models.PositiveIntegerField(default=0)
    calories = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-cooked_on", "-created_at"]

    def __str__(self):
        return f"{self.user} - {self.recipe_name or 'Masak'} ({self.cooked_on})"


class CookingStreak(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cooking_streak")
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_cooked_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user}: {self.current_streak} hari"

    @property
    def active_streak(self):
        """Streak yang ditampilkan. Jadi 0 kalau sudah lewat dari kemarin."""
        if not self.last_cooked_on:
            return 0
        if self.last_cooked_on < timezone.localdate() - timedelta(days=1):
            return 0
        return self.current_streak

    def register(self, day):
        """Panggil setiap kali user selesai memasak pada tanggal `day`."""
        if self.last_cooked_on == day:
            return  # sudah dihitung hari ini
        if self.last_cooked_on == day - timedelta(days=1):
            self.current_streak += 1
        else:
            self.current_streak = 1
        self.last_cooked_on = day
        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.save()


class Badge(models.Model):
    class Kind(models.TextChoices):
        STREAK = "streak", "Streak hari berturut-turut"
        TOTAL = "total", "Total masakan"

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=160)
    icon = models.ImageField(upload_to="badges/", blank=True, null=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    threshold = models.PositiveIntegerField(help_text="Jumlah hari (streak) atau jumlah masakan (total)")

    class Meta:
        ordering = ["kind", "threshold"]

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")

    def __str__(self):
        return f"{self.user} - {self.badge}"