import uuid

from django.db import transaction
from django.utils import timezone

import uuid
from django.db import transaction, IntegrityError


from .models import Badge, CookingLog, CookingStreak, UserBadge


@transaction.atomic # Decorator ini memastikan perubahan database di dalam fungsi diperlakukan sebagai satu transaksi.
def record_cook(user, recipe_name="", protein_g=0, carbs_g=0, fat_g=0, calories=0, day=None, request_id=None,):
    """
    Dipanggil saat user mengonfirmasi selesai memasak.
    Mencatat log, memperbarui streak, dan memberi badge baru.
    Mengembalikan list Badge yang baru didapat (untuk ditampilkan sebagai notifikasi).
    """
    day = day or timezone.localdate() # menentukan tanggal memasak

    # membuat uuid
    if request_id is None:
        request_id = uuid.uuid4()

    # memeriksa cookinglog yg sudah ada 
    existing = CookingLog.objects.filter(
        request_id=request_id
    ).first()

    if existing:
        if existing.user_id != user.pk:
            raise ValueError("Request ID sudah digunakan akun lain.")
        return []

    # membuat cookinglog dan mneyimpan ke data base
    log = CookingLog.objects.create(
        user=user, recipe_name=recipe_name, cooked_on=day,
        protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g, calories=calories, request_id=request_id,
    )

    try:
        with transaction.atomic():
            log
            # memperbarui cooking streak
            streak, _ = CookingStreak.objects.get_or_create(user=user)
            streak.register(day)

            # memberikan badge
            return award_badges(user, streak)

    except IntegrityError:
       
        existing = CookingLog.objects.filter(
            request_id=request_id
        ).first()

        if existing and existing.user_id == user.pk:
            return []

       
        raise


def award_badges(user, streak=None):
    streak = streak or CookingStreak.objects.get_or_create(user=user)[0]
    # menghitung total aktivitas pengguna
    total = CookingLog.objects.filter(user=user).count()
    # mengambil id badge lalu memeriksa keanggotaan 
    owned = set(UserBadge.objects.filter(user=user).values_list("badge_id", flat=True))

    new = []
    # memeriksa badge
    for badge in Badge.objects.exclude(id__in=owned):
        value = streak.longest_streak if badge.kind == Badge.Kind.STREAK else total
        if value >= badge.threshold:
            UserBadge.objects.create(user=user, badge=badge)
            new.append(badge)
    return new