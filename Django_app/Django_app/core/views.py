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
from .geo_translations import SEASON_NAMES, SOIL_NAMES, STATE_NAMES, localize_options
from .models import GENDER_CHOICES, LANGUAGE_CHOICES, Profile
from .translations import get_translations


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
    profile, _ = Profile.objects.get_or_create(
        user=request.user, defaults={"name": request.user.email}
    )
    context = ml.get_form_options()
    context.update(_localized_form_options(request, context, profile=profile))
    context["profile"] = profile
    return render(request, "index.html", context)


@login_required(login_url="core:login")
def profile_page(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user, defaults={"name": request.user.email}
    )
    lang = profile.preferred_language
    context = {
        "profile": profile,
        "state_localized": STATE_NAMES.get(lang, {}).get(profile.state, profile.state),
        "default_soil_localized": SOIL_NAMES.get(lang, {}).get(profile.default_soil, profile.default_soil),
    }
    return render(request, "profile.html", context)


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

    translations = get_translations(profile.preferred_language)
    form.fields["gender"].choices = [("", translations["gender_select_placeholder"])] + list(GENDER_CHOICES)

    form_options = ml.get_form_options()
    context = {"form": form, **form_options}
    context.update(_localized_form_options(request, form_options, profile=profile))
    return render(request, "edit_profile.html", context)


def _localized_form_options(request, form_options, profile=None):
    """Returns {states,soil_types,seasons}_localized: [(value, label), ...]
    pairs where value is the original English dataset value (submitted to
    the ML model) and label is translated for the request's language."""
    if profile is None and request.user.is_authenticated:
        profile, _ = Profile.objects.get_or_create(
            user=request.user, defaults={"name": request.user.email}
        )
    lang = profile.preferred_language if profile else "en"

    return {
        "states_localized": localize_options(form_options["states"], STATE_NAMES, lang),
        "soil_types_localized": localize_options(form_options["soil_types"], SOIL_NAMES, lang),
        "seasons_localized": localize_options(form_options["seasons"], SEASON_NAMES, lang),
    }


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

    profile, _ = Profile.objects.get_or_create(
        user=request.user, defaults={"name": request.user.email}
    )
    if profile.preferred_language != "en":
        results = ai.translate_crop_tips(results, profile.preferred_language)

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
def set_language(request):
    try:
        language = json.loads(request.body).get("language")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)

    if language not in dict(LANGUAGE_CHOICES):
        return JsonResponse({"error": "Invalid language."}, status=400)

    profile, _ = Profile.objects.get_or_create(
        user=request.user, defaults={"name": request.user.email}
    )
    profile.preferred_language = language
    profile.save(update_fields=["preferred_language"])
    return JsonResponse({"language": profile.preferred_language})


@login_required(login_url="core:login")
@require_POST
def ask_ai_api(request):
    try:
        messages = json.loads(request.body)["messages"]
        if not isinstance(messages, list):
            raise ValueError
    except (json.JSONDecodeError, KeyError, ValueError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    profile, _ = Profile.objects.get_or_create(
        user=request.user, defaults={"name": request.user.email}
    )
    try:
        answer = ai.ask_agri_question(messages, profile.preferred_language)
    except ai.AskAIError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"answer": answer})
