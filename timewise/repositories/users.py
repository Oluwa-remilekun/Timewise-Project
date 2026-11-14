"""User account storage. Credential hashing lives in ``timewise.auth``."""

from timewise.clock import utc_now
from timewise.database import get_database
from timewise.models import User
from timewise.repositories import new_id


def create_user(name: str, username: str, password_hash: str, recovery_code_hash: str) -> User:
    user = User(new_id(), name, username)
    db = get_database()
    db.execute(
        f"""
        INSERT INTO {db.table("users")}
            (id, name, username, password_hash, recovery_code_hash, created_at)
        VALUES
            (@id, @name, @username, @password_hash, @recovery_code_hash, @created_at)
        """,
        {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "password_hash": password_hash,
            "recovery_code_hash": recovery_code_hash,
            "created_at": utc_now(),
        },
    )
    return user


def find_credentials(username: str) -> dict | None:
    """Return the full user row, including credential hashes, or None."""
    db = get_database()
    rows = db.query(
        f"""
        SELECT id, name, username, password_hash, recovery_code_hash
        FROM {db.table("users")}
        WHERE username = @username
        """,
        {"username": username},
    )
    return rows[0] if rows else None


def update_credentials(user_id: str, password_hash: str, recovery_code_hash: str) -> None:
    db = get_database()
    db.execute(
        f"""
        UPDATE {db.table("users")}
        SET password_hash = @password_hash, recovery_code_hash = @recovery_code_hash
        WHERE id = @id
        """,
        {
            "id": user_id,
            "password_hash": password_hash,
            "recovery_code_hash": recovery_code_hash,
        },
    )
