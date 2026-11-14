"""Reminder storage and scheduling."""

from datetime import datetime, timedelta

from timewise.constants import REMINDER_SOURCE_TYPES
from timewise.database import get_database
from timewise.errors import ValidationError
from timewise.models import Reminder
from timewise.repositories import new_id
from timewise.validation import clean_title, require_choice

_COLUMNS = "id, title, source_type, remind_at, repeat_interval_minutes"


def _validate_interval(repeat_interval_minutes: int) -> int:
    repeat_interval_minutes = int(repeat_interval_minutes)
    if repeat_interval_minutes < 0:
        raise ValidationError("Repeat interval cannot be negative.")
    return repeat_interval_minutes


def add_reminder(
    user_id: str,
    title: str,
    source_type: str,
    remind_at: datetime,
    repeat_interval_minutes: int = 0,
) -> Reminder:
    reminder = Reminder(
        new_id(),
        clean_title(title, "Reminder title"),
        require_choice(source_type, REMINDER_SOURCE_TYPES, "Reminder type"),
        remind_at,
        _validate_interval(repeat_interval_minutes),
    )
    db = get_database()
    db.execute(
        f"""
        INSERT INTO {db.table("reminders")}
            (id, user_id, title, source_type, remind_at, repeat_interval_minutes)
        VALUES
            (@id, @user_id, @title, @source_type, @remind_at, @repeat_interval_minutes)
        """,
        {
            "id": reminder.id,
            "user_id": user_id,
            "title": reminder.title,
            "source_type": reminder.source_type,
            "remind_at": reminder.remind_at,
            "repeat_interval_minutes": reminder.repeat_interval_minutes,
        },
    )
    return reminder


def update_reminder(
    user_id: str, reminder_id: str, remind_at: datetime, repeat_interval_minutes: int
) -> None:
    db = get_database()
    db.execute(
        f"""
        UPDATE {db.table("reminders")}
        SET remind_at = @remind_at, repeat_interval_minutes = @repeat_interval_minutes
        WHERE id = @id AND user_id = @user_id
        """,
        {
            "id": reminder_id,
            "user_id": user_id,
            "remind_at": remind_at,
            "repeat_interval_minutes": _validate_interval(repeat_interval_minutes),
        },
    )


def delete_reminder(user_id: str, reminder_id: str) -> None:
    db = get_database()
    db.execute(
        f"DELETE FROM {db.table('reminders')} WHERE id = @id AND user_id = @user_id",
        {"id": reminder_id, "user_id": user_id},
    )


def list_reminders(user_id: str) -> list[Reminder]:
    db = get_database()
    rows = db.query(
        f"""
        SELECT {_COLUMNS}
        FROM {db.table("reminders")}
        WHERE user_id = @user_id
        ORDER BY remind_at
        """,
        {"user_id": user_id},
    )
    return [Reminder(**row) for row in rows]


def next_occurrence(reminder: Reminder, now: datetime) -> datetime | None:
    """Return the first occurrence after ``now``, or None for a one-off reminder."""
    if not reminder.is_repeating:
        return None
    interval = timedelta(minutes=reminder.repeat_interval_minutes)
    if reminder.remind_at > now:
        return reminder.remind_at
    missed_intervals = (now - reminder.remind_at) // interval + 1
    return reminder.remind_at + missed_intervals * interval


def acknowledge_reminder(user_id: str, reminder: Reminder, now: datetime) -> None:
    """Dismiss a due reminder: reschedule it if it repeats, otherwise remove it."""
    upcoming = next_occurrence(reminder, now)
    if upcoming is None:
        delete_reminder(user_id, reminder.id)
    else:
        update_reminder(user_id, reminder.id, upcoming, reminder.repeat_interval_minutes)
