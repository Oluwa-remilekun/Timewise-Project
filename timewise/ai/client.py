"""Thin wrapper around the Gemini API (Google AI Studio free tier)."""

import logging
from functools import lru_cache

from google import genai
from google.genai import types

from timewise.config import get_settings

logger = logging.getLogger(__name__)


class AIUnavailableError(RuntimeError):
    """The model could not be reached or returned nothing usable.

    ``reason`` is a short explanation that is safe to show to the user.
    """

    def __init__(self, message: str, reason: str = "Gemini is unavailable right now."):
        super().__init__(message)
        self.reason = reason


def explain_failure(error: Exception, model: str) -> str:
    """Translate a Gemini SDK error into a short, user-facing reason."""
    detail = str(error).lower()
    if "api key" in detail or "api_key" in detail or "permission" in detail:
        return "Gemini rejected the API key. Create a new key and update GEMINI_API_KEY."
    if "not found" in detail or "404" in detail:
        return f"The model {model!r} is not available. Set GEMINI_MODEL to another model."
    if "quota" in detail or "resource_exhausted" in detail or "429" in detail:
        return "The Gemini free-tier limit was reached. Try again in a minute."
    return "Gemini could not be reached. Try again in a moment."


def is_configured() -> bool:
    return bool(get_settings().gemini_api_key)


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    return genai.Client(api_key=get_settings().gemini_api_key)


def generate_text(
    prompt: str,
    *,
    system_instruction: str,
    temperature: float = 0.7,
    json_output: bool = False,
) -> str:
    """Send one prompt to the configured Gemini model and return its text reply."""
    if not is_configured():
        raise AIUnavailableError(
            "GEMINI_API_KEY is not set.", reason="Set GEMINI_API_KEY to enable AI features."
        )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json" if json_output else "text/plain",
    )
    model = get_settings().gemini_model
    try:
        response = _get_client().models.generate_content(
            model=model, contents=prompt, config=config
        )
        text = (response.text or "").strip()
    except Exception as error:  # network, quota and API errors all degrade the same way
        logger.warning("Gemini request failed: %s", error)
        raise AIUnavailableError(
            f"Gemini request failed: {error}", reason=explain_failure(error, model)
        ) from error

    if not text:
        raise AIUnavailableError(
            "Gemini returned an empty response.", reason="Gemini returned an empty reply."
        )
    return text
