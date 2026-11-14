"""Input validation shared by the repositories."""

from collections.abc import Collection

from timewise.constants import MAX_TITLE_LENGTH
from timewise.errors import ValidationError


def clean_title(value: str, field: str = "Title") -> str:
    title = (value or "").strip()
    if not title:
        raise ValidationError(f"{field} is required.")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError(f"{field} must be {MAX_TITLE_LENGTH} characters or fewer.")
    return title


def require_choice(value: str, choices: Collection[str], field: str) -> str:
    if value not in choices:
        raise ValidationError(f"{field} must be one of: {', '.join(choices)}.")
    return value
