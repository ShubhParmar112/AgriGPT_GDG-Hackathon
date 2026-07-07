from django.contrib.auth.models import User
from django.db import models

GENDER_CHOICES = [
    ("Male", "Male"),
    ("Female", "Female"),
    ("Other", "Other"),
]

THEME_CHOICES = [
    ("light", "Light"),
    ("dark", "Dark"),
]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)
    theme = models.CharField(max_length=5, choices=THEME_CHOICES, default="light")

    age = models.PositiveSmallIntegerField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    taluka = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    farm_size_acres = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    preferred_language = models.CharField(max_length=50, blank=True)
    default_soil = models.CharField(max_length=50, blank=True)
    main_crops = models.CharField(max_length=255, blank=True, help_text="Comma-separated crop names")

    @property
    def main_crops_list(self):
        return [crop.strip() for crop in self.main_crops.split(",") if crop.strip()]

    def __str__(self):
        return self.name or self.user.email
