"""Persistent login session storage. Only token hashes are stored."""

from datetime import datetime

from timewise.database import get_database
from timewise.models import User
from timewise.repositories import new_id


def create_session(user_id: str, token_hash: str, expires_at: datetime) -> None:
    db = get_database()
    db.execute(
        f"""
        INSERT INTO {db.table("sessions")} (id, user_id, token_hash, expires_at)
        VALUES (@id, @user_id, @token_hash, @expires_at)
        """,
        {
            "id": new_id(),
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
        },
    )


def find_session_user(token_hash: str, now: datetime) -> User | None:
    db = get_database()
    rows = db.query(
        f"""
        SELECT u.id, u.name, u.username
        FROM {db.table("sessions")} AS s
        JOIN {db.table("users")} AS u ON u.id = s.user_id
        WHERE s.token_hash = @token_hash AND s.expires_at > @now
        """,
        {"token_hash": token_hash, "now": now},
    )
    return User(**rows[0]) if rows else None


def delete_session(token_hash: str) -> None:
    db = get_database()
    db.execute(
        f"DELETE FROM {db.table('sessions')} WHERE token_hash = @token_hash",
        {"token_hash": token_hash},
    )


def delete_user_sessions(user_id: str) -> None:
    db = get_database()
    db.execute(
        f"DELETE FROM {db.table('sessions')} WHERE user_id = @user_id",
        {"user_id": user_id},
    )


def delete_expired_sessions(now: datetime) -> None:
    db = get_database()
    db.execute(
        f"DELETE FROM {db.table('sessions')} WHERE expires_at <= @now",
        {"now": now},
    )
