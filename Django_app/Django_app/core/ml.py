"""Loads the trained crop-recommendation model and the dataset it was
trained on, and exposes a simple predict_crops() function.

The notebook that produced NN_Model.h5 label-encoded four input columns
(State, Soil Type, Temperature Range, Season) and the "Suggested Crops"
output column with plain sklearn LabelEncoders that were never persisted.
LabelEncoder assigns codes by sorting each column's unique values, which
is deterministic, so re-fitting encoders against the same source
spreadsheet at load time reproduces the exact training-time encoding.
"""

import threading
from pathlib import Path

import numpy as np
import pandas as pd
from django.conf import settings
from sklearn.preprocessing import LabelEncoder

from .crop_info import CROP_INFO

MODEL_PATH = Path(settings.BASE_DIR) / "ml_model" / "NN_Model.h5"
DATA_PATH = Path(settings.BASE_DIR) / "ml_model" / "crop_suggestions_all_india.xlsx"

STATE_COL = "State"
SOIL_COL = "Soil Type"
TEMP_COL = "Temperature Range (°C)"
SEASON_COL = "Season"
CROPS_COL = "Suggested Crops"

# The dataset carries a Temperature Range column that the UI intentionally
# doesn't expose (the product spec calls for exactly three inputs). Each
# season is mapped to a representative temperature band instead.
SEASON_TEMPERATURE = {
    "Kharif": "25-30",
    "Rabi": "15-20",
    "Zaid": "30-35",
}

SUITABILITY_TIERS = [
    {"label": "Highly Recommended", "badgeClass": "bg-deep-green text-white dark:bg-light-green dark:text-deep-green-dark"},
    {"label": "Recommended", "badgeClass": "bg-light-green/70 text-deep-green-dark dark:bg-slate-700 dark:text-light-green"},
    {"label": "Suitable", "badgeClass": "bg-soft-beige text-deep-green-dark border border-light-green dark:bg-slate-700 dark:text-gray-200 dark:border-slate-600"},
]

_lock = threading.Lock()
_state = {}


def _load():
    if _state:
        return
    with _lock:
        if _state:
            return

        data = pd.read_excel(DATA_PATH)

        encoders = {}
        for col in (STATE_COL, SOIL_COL, TEMP_COL, SEASON_COL, CROPS_COL):
            encoder = LabelEncoder()
            encoder.fit(data[col])
            encoders[col] = encoder

        from tensorflow import keras
        model = keras.models.load_model(MODEL_PATH)

        _state["encoders"] = encoders
        _state["model"] = model
        _state["states"] = sorted(data[STATE_COL].unique().tolist())
        _state["soil_types"] = sorted(data[SOIL_COL].unique().tolist())
        _state["seasons"] = ["Kharif", "Rabi", "Zaid"]


def get_form_options():
    _load()
    return {
        "states": _state["states"],
        "soil_types": _state["soil_types"],
        "seasons": _state["seasons"],
    }


def predict_crops(state, soil, season, max_results=3, min_confidence=3.0):
    """Returns a list of {name, emoji, confidence, suitability, ...} dicts,
    ranked by the model's predicted probability, deduplicated by crop name.
    """
    _load()
    encoders = _state["encoders"]
    model = _state["model"]
    temperature = SEASON_TEMPERATURE.get(season, "25-30")

    row = [
        encoders[STATE_COL].transform([state])[0],
        encoders[SOIL_COL].transform([soil])[0],
        encoders[TEMP_COL].transform([temperature])[0],
        encoders[SEASON_COL].transform([season])[0],
    ]
    probabilities = model.predict(np.array([row]), verbose=0)[0]
    ranked_indices = np.argsort(probabilities)[::-1]
    crop_encoder = encoders[CROPS_COL]

    results = []
    seen_names = set()
    for rank, idx in enumerate(ranked_indices):
        if len(results) >= max_results:
            break
        confidence = float(probabilities[idx]) * 100
        if rank > 0 and confidence < min_confidence:
            break

        bundle = crop_encoder.inverse_transform([idx])[0]
        tier = SUITABILITY_TIERS[min(rank, len(SUITABILITY_TIERS) - 1)]

        for name in (part.strip() for part in bundle.split(",")):
            if name in seen_names:
                continue
            seen_names.add(name)
            info = CROP_INFO.get(name, {})
            results.append({
                "name": name,
                "emoji": info.get("emoji", "🌱"),
                "confidence": round(confidence, 1),
                "suitability": tier,
                "sowing": info.get("sowing", "Varies by region"),
                "harvest": info.get("harvest", "Varies by region"),
                "water": info.get("water", "Medium"),
                "climate": info.get("climate", "Moderate"),
                "soil": info.get("soil", soil),
                "difficulty": info.get("difficulty", 2),
                "profitability": info.get("profitability", 2),
                "tips": info.get("tips", "Follow local agricultural extension guidance for best results."),
            })

    return results
