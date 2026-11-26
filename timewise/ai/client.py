"""Thin wrapper around the Gemini API (Google AI Studio free tier)."""

import logging
import re
from collections.abc import Iterable
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


# Models that cannot answer a plain text prompt, or are not meant for production use.
_UNSUITABLE_MODELS = ("image", "tts", "audio", "live", "embedding", "robotics", "computer-use")
_UNSTABLE_MODELS = ("preview", "exp")

# The model actually in use. It differs from the configured one only after the
# configured model was reported missing and a replacement was discovered.
_state: dict[str, str | None] = {"model": None}


def _version_key(name: str) -> tuple[float, int]:
    """Sort by model generation (the 2.5 in gemini-2.5-flash), then prefer the shortest alias."""
    match = re.search(r"\d+(?:\.\d+)?", name)
    return (float(match.group()) if match else 0.0), -len(name)


def choose_model(names: Iterable[str]) -> str | None:
    """Pick the newest stable Flash model from the names a key can use.

    Falls back to Flash-Lite, then any text model, and to preview models only
    when nothing stable is available.
    """
    usable = [
        name
        for name in names
        if name.startswith("gemini") and not any(word in name for word in _UNSUITABLE_MODELS)
    ]
    stable = [name for name in usable if not any(word in name for word in _UNSTABLE_MODELS)]
    candidates = stable or usable
    preferences = (
        lambda name: "flash" in name and "lite" not in name,
        lambda name: "flash" in name,
        lambda name: True,
    )
    for preferred in preferences:
        matches = [name for name in candidates if preferred(name)]
        if matches:
            return max(matches, key=_version_key)
    return None


def _list_text_models() -> list[str]:
    names = []
    for model in _get_client().models.list():
        actions = model.supported_actions or []
        if "generateContent" in actions and model.name:
            names.append(model.name.removeprefix("models/"))
    return names


def _is_missing_model(error: Exception) -> bool:
    detail = str(error).lower()
    return "404" in detail or "not_found" in detail or "not found" in detail


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
    model = _state["model"] or get_settings().gemini_model
    try:
        text = _generate(model, prompt, config)
    except Exception as error:  # network, quota and API errors all degrade the same way
        replacement = _replacement_for(model, error)
        if replacement is None:
            logger.warning("Gemini request failed: %s", error)
            raise AIUnavailableError(
                f"Gemini request failed: {error}", reason=explain_failure(error, model)
            ) from error
        return generate_text(
            prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            json_output=json_output,
        )

    if not text:
        raise AIUnavailableError(
            "Gemini returned an empty response.", reason="Gemini returned an empty reply."
        )
    return text


def _generate(model: str, prompt: str, config: types.GenerateContentConfig) -> str:
    response = _get_client().models.generate_content(model=model, contents=prompt, config=config)
    return (response.text or "").strip()


def _replacement_for(model: str, error: Exception) -> str | None:
    """Switch to an available model when ``model`` does not exist for this key.

    Returns the new model name, or None when no switch was made.
    """
    if not _is_missing_model(error) or _state["model"] not in (None, model):
        return None
    try:
        replacement = choose_model(_list_text_models())
    except Exception as list_error:
        logger.warning("Could not list Gemini models: %s", list_error)
        return None
    if replacement is None or replacement == model:
        return None
    logger.warning("Gemini model %r is unavailable; using %r instead.", model, replacement)
    _state["model"] = replacement
    return replacement
