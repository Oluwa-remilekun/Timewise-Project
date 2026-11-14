"""Display formatting helpers."""

from datetime import date, datetime, time

from timewise.analytics import format_duration


def format_time(value: datetime | time) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def format_date(value: date) -> str:
    return f"{value:%a, %b} {value.day}"


def format_datetime(value: datetime) -> str:
    return f"{format_date(value)} at {format_time(value)}"


def format_repeat(interval_minutes: int) -> str:
    if interval_minutes <= 0:
        return "Once"
    return f"Every {format_duration(interval_minutes)}"
