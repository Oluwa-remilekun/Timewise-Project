"""Turn a natural-language sentence into a calendar event draft."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from timewise.ai import prompts
from timewise.ai.client import AIUnavailableError, generate_text

logger = logging.getLogger(__name__)

DEFAULT_DURATION = timedelta(hours=1)
_INVALID_REPLY = "Gemini replied, but not with a usable event. Try rephrasing it."
_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass(frozen=True)
class EventDraft:
    title: str
    starts_at: datetime
    ends_at: datetime


def _read_payload(reply: str) -> dict:
    """Decode the model's JSON reply, tolerating code fences and a one-item list."""
    payload = json.loads(_CODE_FENCE.sub("", reply.strip()))
    if isinstance(payload, list) and len(payload) == 1:
        payload = payload[0]
    if not isinstance(payload, dict):
        raise TypeError("The reply is not a JSON object.")
    return payload


def _read_time(value: object) -> datetime:
    return datetime.fromisoformat(str(value).strip().replace("Z", "")).replace(tzinfo=None)


def parse_event(text: str, now: datetime) -> EventDraft:
    """Extract an event from ``text``. Raises AIUnavailableError on any failure."""
    reply = generate_text(
        prompts.event_parser_prompt(text, now),
        system_instruction=prompts.EVENT_PARSER_INSTRUCTION,
        temperature=0,
        json_output=True,
    )
    try:
        payload = _read_payload(reply)
        starts_at = _read_time(payload["start"])
        end = payload.get("end")
        ends_at = _read_time(end) if end else starts_at + DEFAULT_DURATION
        draft = EventDraft(str(payload["title"]).strip(), starts_at, ends_at)
    except (KeyError, TypeError, ValueError) as error:
        logger.warning("Unusable event reply %r: %s", reply, error)
        raise AIUnavailableError(
            "The model reply was not a valid event.", _INVALID_REPLY
        ) from error

    if not draft.title or draft.ends_at <= draft.starts_at:
        logger.warning("Unusable event reply %r", reply)
        raise AIUnavailableError("The model reply was not a valid event.", _INVALID_REPLY)
    return draft
