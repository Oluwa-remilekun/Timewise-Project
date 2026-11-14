"""Backend-neutral table definitions.

Column types use BigQuery names; the SQLite backend maps them to its own.
"""

TABLES: dict[str, dict[str, str]] = {
    "users": {
        "id": "STRING",
        "name": "STRING",
        "username": "STRING",
        "password_hash": "STRING",
        "recovery_code_hash": "STRING",
        "created_at": "DATETIME",
    },
    "sessions": {
        "id": "STRING",
        "user_id": "STRING",
        "token_hash": "STRING",
        "expires_at": "DATETIME",
    },
    "activities": {
        "id": "STRING",
        "user_id": "STRING",
        "title": "STRING",
        "category": "STRING",
        "duration_minutes": "INT64",
        "activity_date": "DATE",
        "created_at": "DATETIME",
    },
    "tasks": {
        "id": "STRING",
        "user_id": "STRING",
        "title": "STRING",
        "description": "STRING",
        "category": "STRING",
        "due_date": "DATE",
        "is_completed": "BOOL",
        "created_at": "DATETIME",
    },
    "events": {
        "id": "STRING",
        "user_id": "STRING",
        "title": "STRING",
        "starts_at": "DATETIME",
        "ends_at": "DATETIME",
    },
    "reminders": {
        "id": "STRING",
        "user_id": "STRING",
        "title": "STRING",
        "source_type": "STRING",
        "remind_at": "DATETIME",
        "repeat_interval_minutes": "INT64",
    },
}
