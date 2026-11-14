"""Calendar event storage."""

from datetime import datetime

from timewise.database import get_database
from timewise.errors import ValidationError
from timewise.models import Event
from timewise.repositories import new_id
from timewise.validation import clean_title

_COLUMNS = "id, title, starts_at, ends_at"


def _validate(title: str, starts_at: datetime, ends_at: datetime) -> str:
    title = clean_title(title, "Event title")
    if ends_at <= starts_at:
        raise ValidationError("The event must end after it starts.")
    return title


def add_event(user_id: str, title: str, starts_at: datetime, ends_at: datetime) -> Event:
    event = Event(new_id(), _validate(title, starts_at, ends_at), starts_at, ends_at)
    db = get_database()
    db.execute(
        f"""
        INSERT INTO {db.table("events")} (id, user_id, title, starts_at, ends_at)
        VALUES (@id, @user_id, @title, @starts_at, @ends_at)
        """,
        {
            "id": event.id,
            "user_id": user_id,
            "title": event.title,
            "starts_at": event.starts_at,
            "ends_at": event.ends_at,
        },
    )
    return event


def update_event(
    user_id: str, event_id: str, title: str, starts_at: datetime, ends_at: datetime
) -> None:
    title = _validate(title, starts_at, ends_at)
    db = get_database()
    db.execute(
        f"""
        UPDATE {db.table("events")}
        SET title = @title, starts_at = @starts_at, ends_at = @ends_at
        WHERE id = @id AND user_id = @user_id
        """,
        {
            "id": event_id,
            "user_id": user_id,
            "title": title,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    )


def delete_event(user_id: str, event_id: str) -> None:
    db = get_database()
    db.execute(
        f"DELETE FROM {db.table('events')} WHERE id = @id AND user_id = @user_id",
        {"id": event_id, "user_id": user_id},
    )


def get_event(user_id: str, event_id: str) -> Event | None:
    db = get_database()
    rows = db.query(
        f"""
        SELECT {_COLUMNS}
        FROM {db.table("events")}
        WHERE id = @id AND user_id = @user_id
        """,
        {"id": event_id, "user_id": user_id},
    )
    return Event(**rows[0]) if rows else None


def list_events(user_id: str) -> list[Event]:
    db = get_database()
    rows = db.query(
        f"""
        SELECT {_COLUMNS}
        FROM {db.table("events")}
        WHERE user_id = @user_id
        ORDER BY starts_at
        """,
        {"user_id": user_id},
    )
    return [Event(**row) for row in rows]


def list_upcoming_events(user_id: str, now: datetime) -> list[Event]:
    db = get_database()
    rows = db.query(
        f"""
        SELECT {_COLUMNS}
        FROM {db.table("events")}
        WHERE user_id = @user_id AND ends_at >= @now
        ORDER BY starts_at
        """,
        {"user_id": user_id, "now": now},
    )
    return [Event(**row) for row in rows]
