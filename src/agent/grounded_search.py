"""
Google Search-Grounded Gemini Queries.

The installed `google-generativeai` SDK (deprecated, but required by
model_rotator.py) cannot reliably trigger the `google_search` grounding tool:
passing a `genai.protos.Tool(google_search=...)` silently produces an
ungrounded response, and passing a raw dict raises a proto validation error.
A direct REST call to the same v1beta endpoint with
`{"tools": [{"google_search": {}}]}` works correctly and returns real,
current search results. This module isolates that workaround so callers
don't need to know about the SDK limitation.
"""

import requests
from src.agent.model_rotator import get_current_api_key

# Models confirmed (by manual testing) to support google_search grounding
# via the raw REST call. Tried in order; the "2.0" generation models in
# Config.GEMINI_MODELS_FALLBACK are excluded here as they returned zero
# free-tier quota entirely during testing.
GROUNDED_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def generate_grounded_content(prompt: str, timeout: int = 30) -> str:
    """
    Queries Gemini with live Google Search grounding enabled.

    Args:
        prompt: The prompt to send. Should explicitly ask the model to
            search for current information, since grounding is only
            triggered when the model judges it necessary.
        timeout: Per-request timeout in seconds.

    Returns:
        The text response.

    Raises:
        RuntimeError: If every candidate model fails (quota, network, etc.).
    """
    key = get_current_api_key()
    if not key:
        raise RuntimeError("No Gemini API key available for grounded search.")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
    }

    last_error = None
    for model_name in GROUNDED_MODELS:
        url = f"{API_BASE}/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()

            candidates = data.get("candidates") or []
            if not candidates:
                raise RuntimeError(f"no candidates (promptFeedback={data.get('promptFeedback')})")

            parts = candidates[0].get("content", {}).get("parts") or []
            if not parts:
                raise RuntimeError(f"no text parts (finishReason={candidates[0].get('finishReason')})")

            text = parts[0].get("text", "")
            if text and text.strip():
                return text
            raise RuntimeError("empty text part")
        except Exception as e:
            last_error = f"{model_name}: {e}"
            continue

    raise RuntimeError(f"Grounded search failed on all candidate models: {last_error}")
