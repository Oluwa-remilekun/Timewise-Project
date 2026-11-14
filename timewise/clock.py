"""Time helpers. Server-side timestamps are stored as naive UTC datetimes."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)
