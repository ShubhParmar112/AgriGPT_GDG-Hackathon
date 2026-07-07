import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import ai, ml
from .forms import ProfileForm, SignUpForm
from .models import Profile

LANGUAGES = [
    "Hindi", "English", "Marathi", "Bengali", "Telugu", "Tamil", "Gujarati",
    "Kannada", "Malayalam", "Punjabi", "Odia", "Assamese",
]


def signup_page(request):
    if request.user.is_authenticated:
        return redirect("core:main")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        user = User.objects.create_user(
            username=data["email"], email=data["email"], password=data["password"]
        )
        Profile.objects.create(user=user, name=data["name"], phone=data["phone"])
        login(request, user)
        return redirect("core:main")

    return render(request, "signup.html", {"form": form})


def login_page(request):
    if request.user.is_authenticated:
        return redirect("core:main")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect("core:main")
        messages.error(request, "Invalid email or password.")

    return render(request, "login.html")


@login_required(login_url="core:login")
def logout_view(request):
    logout(request)
    return redirect("core:login")


@login_required(login_url="core:login")
def main_page(request):
    context = ml.get_form_options()
    return render(request, "index.html", context)


@login_required(login_url="core:login")
def profile_page(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user, defaults={"name": request.user.email}
    )
    return render(request, "profile.html", {"profile": profile})


@login_required(login_url="core:login")
def edit_profile_page(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user, defaults={"name": request.user.email}
    )
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("core:profile")

    context = {"form": form, "languages": LANGUAGES, **ml.get_form_options()}
    return render(request, "edit_profile.html", context)


@login_required(login_url="core:login")
@require_POST
def recommend_crops_api(request):
    try:
        payload = json.loads(request.body)
        state = payload["state"]
        soil = payload["soil"]
        season = payload["season"]
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    try:
        results = ml.predict_crops(state, soil, season)
    except ValueError:
        return JsonResponse({"error": "Unrecognised state, soil type, or season."}, status=400)

    return JsonResponse({"results": results})


@login_required(login_url="core:login")
@require_POST
def set_theme(request):
    try:
        theme = json.loads(request.body).get("theme")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)

    if theme not in ("light", "dark"):
        return JsonResponse({"error": "Invalid theme."}, status=400)

    profile, _ = Profile.objects.get_or_create(
        user=request.user, defaults={"name": request.user.email}
    )
    profile.theme = theme
    profile.save(update_fields=["theme"])
    return JsonResponse({"theme": profile.theme})


@login_required(login_url="core:login")
@require_POST
def ask_ai_api(request):
    try:
        messages = json.loads(request.body)["messages"]
        if not isinstance(messages, list):
            raise ValueError
    except (json.JSONDecodeError, KeyError, ValueError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    try:
        answer = ai.ask_agri_question(messages)
    except ai.AskAIError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"answer": answer})
