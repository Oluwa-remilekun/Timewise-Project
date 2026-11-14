"""Storage layer. ``get_database`` returns the backend selected in the settings."""

from functools import lru_cache

from timewise.config import get_settings
from timewise.database.base import Database

__all__ = ["Database", "get_database"]


@lru_cache(maxsize=1)
def get_database() -> Database:
    settings = get_settings()
    if settings.database_backend == "bigquery":
        # Imported lazily so local development does not need Google Cloud credentials.
        from timewise.database.bigquery_database import BigQueryDatabase

        database: Database = BigQueryDatabase(settings.bigquery_project, settings.bigquery_dataset)
    else:
        from timewise.database.sqlite_database import SQLiteDatabase

        database = SQLiteDatabase(settings.sqlite_path)
    database.ensure_schema()
    return database
