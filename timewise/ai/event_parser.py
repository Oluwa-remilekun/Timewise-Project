"""Turn a natural-language sentence into a calendar event draft."""

import json
from dataclasses import dataclass
from datetime import datetime

from timewise.ai import prompts
from timewise.ai.client import AIUnavailableError, generate_text


@dataclass(frozen=True)
class EventDraft:
    title: str
    starts_at: datetime
    ends_at: datetime


def parse_event(text: str, now: datetime) -> EventDraft:
    """Extract an event from ``text``. Raises AIUnavailableError on any failure."""
    reply = generate_text(
        prompts.event_parser_prompt(text, now),
        system_instruction=prompts.EVENT_PARSER_INSTRUCTION,
        temperature=0,
        json_output=True,
    )
    try:
        payload = json.loads(reply)
        draft = EventDraft(
            title=str(payload["title"]).strip(),
            starts_at=datetime.fromisoformat(payload["start"]).replace(tzinfo=None),
            ends_at=datetime.fromisoformat(payload["end"]).replace(tzinfo=None),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise AIUnavailableError("The model reply was not a valid event.") from error

    if not draft.title or draft.ends_at <= draft.starts_at:
        raise AIUnavailableError("The model reply was not a valid event.")
    return draft
