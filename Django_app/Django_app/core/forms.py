from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import Profile


class SignUpForm(forms.Form):
    name = forms.CharField(max_length=150)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "picture", "name", "age", "gender", "phone", "state", "district",
            "taluka", "village", "farm_size_acres", "preferred_language",
            "default_soil", "main_crops",
        ]
        widgets = {
            "picture": forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Model field choices setter overwrites widget.choices on construction,
        # so the "Select gender" placeholder has to be applied after the fact.
        from .models import GENDER_CHOICES
        self.fields["gender"].choices = [("", "Select gender")] + list(GENDER_CHOICES)
