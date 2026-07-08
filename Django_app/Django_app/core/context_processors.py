import json

from django.core.exceptions import ObjectDoesNotExist

from .geo_translations import SEASON_NAMES, SOIL_NAMES, STATE_NAMES
from .models import LANGUAGE_CHOICES
from .translations import TRANSLATIONS, get_translations


def i18n(request):
    lang = "en"
    if request.user.is_authenticated:
        try:
            lang = request.user.profile.preferred_language or "en"
        except ObjectDoesNotExist:
            pass

    return {
        "CURRENT_LANG": lang,
        "LANGUAGE_CHOICES": LANGUAGE_CHOICES,
        "t": get_translations(lang),
        "I18N_JSON": json.dumps(TRANSLATIONS),
        "GEO_JSON": json.dumps({
            "states": STATE_NAMES,
            "soils": SOIL_NAMES,
            "seasons": SEASON_NAMES,
        }),
    }
