from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "phone", "state", "default_soil", "theme")
    list_filter = ("theme", "state", "default_soil", "gender")
    search_fields = ("name", "user__email", "phone", "village", "district")
