"""Persistent login sessions backed by random, server-verified tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta

from timewise.clock import utc_now
from timewise.models import User
from timewise.repositories import sessions

REMEMBERED_SESSION_LIFETIME = timedelta(days=30)
DEFAULT_SESSION_LIFETIME = timedelta(days=1)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def start_session(user_id: str, remember: bool) -> tuple[str, datetime]:
    """Create a session and return its token and expiry (naive UTC)."""
    now = utc_now()
    sessions.delete_expired_sessions(now)
    token = secrets.token_urlsafe(32)
    lifetime = REMEMBERED_SESSION_LIFETIME if remember else DEFAULT_SESSION_LIFETIME
    expires_at = now + lifetime
    sessions.create_session(user_id, _hash_token(token), expires_at)
    return token, expires_at


def resolve_session(token: str) -> User | None:
    """Return the user for a valid, unexpired session token."""
    if not token:
        return None
    return sessions.find_session_user(_hash_token(token), utc_now())


def end_session(token: str) -> None:
    if token:
        sessions.delete_session(_hash_token(token))
