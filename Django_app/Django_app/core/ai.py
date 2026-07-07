"""Thin client for the "AgriMitra" Ask AI feature, backed by Groq's
OpenAI-compatible chat completions API. The system prompt is the only
guardrail keeping the assistant scoped to farming/agriculture — there is
no separate classifier.
"""

import requests
from django.conf import settings

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


def ask_agri_question(messages: list) -> str:
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

    try:
        response = requests.post(
            GROQ_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + cleaned,
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
