"""Account registration, sign-in and password recovery."""

import re
import secrets

from timewise.auth.passwords import hash_secret, verify_secret
from timewise.errors import ValidationError
from timewise.models import User
from timewise.repositories import sessions, users

MIN_PASSWORD_LENGTH = 8
_USERNAME_PATTERN = re.compile(r"[a-z0-9_.]{3,30}")


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def normalize_recovery_code(code: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", (code or "").upper())


def generate_recovery_code() -> str:
    """Return a one-time recovery code such as ``3F9A-C21B-7D04``."""
    raw = secrets.token_hex(6).upper()
    return "-".join(raw[index : index + 4] for index in range(0, len(raw), 4))


def _validate_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")


def register(name: str, username: str, password: str) -> tuple[User, str]:
    """Create an account and return it with its recovery code (shown only once)."""
    name = (name or "").strip()
    username = normalize_username(username)
    if not name:
        raise ValidationError("Name is required.")
    if not _USERNAME_PATTERN.fullmatch(username):
        raise ValidationError(
            "Username must be 3-30 characters: letters, numbers, dots or underscores."
        )
    _validate_password(password)
    if users.find_credentials(username):
        raise ValidationError("That username is already taken.")

    recovery_code = generate_recovery_code()
    user = users.create_user(
        name,
        username,
        hash_secret(password),
        hash_secret(normalize_recovery_code(recovery_code)),
    )
    return user, recovery_code


def authenticate(username: str, password: str) -> User | None:
    credentials = users.find_credentials(normalize_username(username))
    if not credentials or not verify_secret(password or "", credentials["password_hash"]):
        return None
    return User(credentials["id"], credentials["name"], credentials["username"])


def reset_password(username: str, recovery_code: str, new_password: str) -> tuple[User, str]:
    """Set a new password using the recovery code, and issue a replacement code.

    Every saved session for the account is signed out.
    """
    _validate_password(new_password)
    credentials = users.find_credentials(normalize_username(username))
    code = normalize_recovery_code(recovery_code)
    if not credentials or not verify_secret(code, credentials["recovery_code_hash"]):
        raise ValidationError("The username or recovery code is incorrect.")

    new_recovery_code = generate_recovery_code()
    users.update_credentials(
        credentials["id"],
        hash_secret(new_password),
        hash_secret(normalize_recovery_code(new_recovery_code)),
    )
    sessions.delete_user_sessions(credentials["id"])
    user = User(credentials["id"], credentials["name"], credentials["username"])
    return user, new_recovery_code
