from django.contrib import admin

from .models import Badge, CookingLog, CookingStreak, UserBadge

admin.site.register(Badge)
admin.site.register(CookingLog)
admin.site.register(CookingStreak)
admin.site.register(UserBadge)