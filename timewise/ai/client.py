"""Thin wrapper around the Gemini API (Google AI Studio free tier)."""

from functools import lru_cache

from google import genai
from google.genai import types

from timewise.config import get_settings


class AIUnavailableError(RuntimeError):
    """The model could not be reached or returned nothing usable."""


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
        raise AIUnavailableError("GEMINI_API_KEY is not set.")

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json" if json_output else "text/plain",
    )
    try:
        response = _get_client().models.generate_content(
            model=get_settings().gemini_model, contents=prompt, config=config
        )
        text = (response.text or "").strip()
    except Exception as error:  # network, quota and API errors all degrade the same way
        raise AIUnavailableError(f"Gemini request failed: {error}") from error

    if not text:
        raise AIUnavailableError("Gemini returned an empty response.")
    return text
