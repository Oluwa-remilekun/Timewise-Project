"""Application settings, read once from environment variables (and a local .env file)."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_COOKIE_SECRET = "timewise-local-development-only"
SUPPORTED_BACKENDS = ("sqlite", "bigquery")


class ConfigurationError(RuntimeError):
    """Raised when the environment is missing a required or valid setting."""


@dataclass(frozen=True)
class Settings:
    database_backend: str
    sqlite_path: Path
    bigquery_project: str
    bigquery_dataset: str
    gemini_api_key: str
    gemini_model: str
    cookie_secret: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    backend = os.getenv("TIMEWISE_DATABASE", "sqlite").strip().lower()
    if backend not in SUPPORTED_BACKENDS:
        raise ConfigurationError(
            f"TIMEWISE_DATABASE must be one of {SUPPORTED_BACKENDS}, got {backend!r}."
        )

    bigquery_project = os.getenv("TIMEWISE_BIGQUERY_PROJECT", "").strip()
    cookie_secret = os.getenv("TIMEWISE_COOKIE_SECRET", "").strip()
    if backend == "bigquery":
        if not bigquery_project:
            raise ConfigurationError(
                "TIMEWISE_BIGQUERY_PROJECT is required when TIMEWISE_DATABASE=bigquery."
            )
        if not cookie_secret:
            raise ConfigurationError(
                "TIMEWISE_COOKIE_SECRET is required when TIMEWISE_DATABASE=bigquery."
            )

    sqlite_path = Path(os.getenv("TIMEWISE_SQLITE_PATH", "data/timewise.db"))
    if not sqlite_path.is_absolute():
        sqlite_path = PROJECT_ROOT / sqlite_path

    return Settings(
        database_backend=backend,
        sqlite_path=sqlite_path,
        bigquery_project=bigquery_project,
        bigquery_dataset=os.getenv("TIMEWISE_BIGQUERY_DATASET", "timewise").strip(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip(),
        cookie_secret=cookie_secret or LOCAL_COOKIE_SECRET,
    )
