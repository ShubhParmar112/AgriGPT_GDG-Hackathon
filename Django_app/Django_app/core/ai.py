"""Thin client for the "AgriMitra" Ask AI feature, backed by Groq's
OpenAI-compatible chat completions API. The system prompt is the only
guardrail keeping the assistant scoped to farming/agriculture — there is
no separate classifier.
"""

import json

import requests
from django.conf import settings

from .translations import LANGUAGE_FULL_NAME

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are AgriMitra, AgriGPT's assistant, built for Indian farmers, "
    "including those with limited literacy. You ONLY answer questions about "
    "farming and agriculture: crops, soil, seeds, sowing/harvest timing, "
    "irrigation and water management, fertilizers and pesticides, plant "
    "diseases and pest control, weather's effect on farming, livestock and "
    "dairy, farm equipment, government agricultural schemes and subsidies, "
    "mandi/market prices, and agricultural best practices.\n\n"
    "If the user asks anything outside these topics (e.g. general trivia, "
    "coding, entertainment, politics, or personal advice unrelated to "
    "farming), politely decline in one short sentence and invite them to "
    "ask a farming question instead. Never answer the off-topic question.\n\n"
    "Keep answers short, simple, and practical — plain language, short "
    "sentences or a few bullet points, no jargon without explanation. "
    "Assume the farmer has a smartphone but limited time and reading "
    "patience."
)

MAX_MESSAGE_LENGTH = 500
MAX_HISTORY_MESSAGES = 12  # last 6 user/assistant turns kept for context


class AskAIError(Exception):
    pass


def ask_agri_question(messages: list, language: str = "en") -> str:
    """messages: [{"role": "user"|"assistant", "content": str}, ...],
    ending with the newest user message. Returns the assistant's reply.
    """
    if not messages or messages[-1].get("role") != "user":
        raise AskAIError("Please type a question first.")

    cleaned = []
    for msg in messages[-MAX_HISTORY_MESSAGES:]:
        role = msg.get("role")
        content = str(msg.get("content", "")).strip()
        if role not in ("user", "assistant") or not content:
            raise AskAIError("Invalid message in conversation.")
        if len(content) > MAX_MESSAGE_LENGTH:
            raise AskAIError(f"Please keep your question under {MAX_MESSAGE_LENGTH} characters.")
        cleaned.append({"role": role, "content": content})

    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise AskAIError("The Ask AI feature isn't configured yet.")

    system_prompt = SYSTEM_PROMPT
    language_name = LANGUAGE_FULL_NAME.get(language, "English")
    # Always state the target language explicitly, even for English —
    # otherwise, once the conversation history contains a reply in a
    # different language, the model tends to keep answering in that
    # language even after the user switches back.
    system_prompt += (
        f"\n\nRespond entirely in {language_name}, using simple everyday words, "
        f"regardless of what language earlier messages in this conversation are in. "
        f"Do not mix in words from other languages or add parenthetical translations."
    )

    try:
        response = requests.post(
            GROQ_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "system", "content": system_prompt}] + cleaned,
                "temperature": 0.4,
                "max_tokens": 500,
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        raise AskAIError("Couldn't reach the AI service. Please try again.") from exc

    if response.status_code != 200:
        raise AskAIError("The AI service had a problem answering that. Please try again.")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise AskAIError("The AI service returned an unexpected response.") from exc


def translate_crop_tips(results: list, language: str) -> list:
    """Translates the free-text fields (crop name, sowing/harvest period,
    and the cultivation tip) of crop recommendation results into the
    given language via one batched Groq call. On any failure (missing
    API key, network error, malformed response) this silently returns
    the original English results — a translation hiccup should never
    break crop recommendations.

    The original English "name" is kept as a stable id (used elsewhere
    to look up emoji/water/difficulty), while the translated name is
    returned separately as "display_name" for the UI to show instead.
    """
    language_name = LANGUAGE_FULL_NAME.get(language)
    api_key = settings.GROQ_API_KEY
    if not language_name or language == "en" or not api_key or not results:
        return results

    fields = [
        {"name": r["name"], "sowing": r["sowing"], "harvest": r["harvest"], "tips": r["tips"]}
        for r in results
    ]

    prompt = (
        f"Translate this JSON array into {language_name}. For each item, add a "
        f"\"display_name\" key with the {language_name} translation of \"name\" (the "
        f"common local name for the crop, not a literal translation), and translate "
        f"the \"sowing\", \"harvest\", and \"tips\" values in place. Keep the original "
        f"\"name\" value UNCHANGED so it can still be used as an id, and keep the JSON "
        f"structure and item order exactly the same. Respond with ONLY the translated "
        f"JSON array, no other text.\n\n{json.dumps(fields)}"
    )

    try:
        response = requests.post(
            GROQ_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2000,
            },
            timeout=20,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        translated = json.loads(content)

        by_name = {item["name"]: item for item in translated if "name" in item}
        merged = []
        for r in results:
            override = by_name.get(r["name"])
            if override:
                merged.append({
                    **r,
                    "display_name": override.get("display_name", r["name"]),
                    "sowing": override.get("sowing", r["sowing"]),
                    "harvest": override.get("harvest", r["harvest"]),
                    "tips": override.get("tips", r["tips"]),
                })
            else:
                merged.append(r)
        return merged
    except Exception:
        return results
