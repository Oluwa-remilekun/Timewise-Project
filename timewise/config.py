"""Application settings, read once from the environment.

Each setting comes from an environment variable (or a local .env file) and falls
back to Streamlit secrets, which is where Streamlit Community Cloud stores them.
"""

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


def _streamlit_secret(name: str) -> str | None:
    """Return a top-level Streamlit secret, or None when there is none."""
    try:
        import streamlit as st

        value = st.secrets.get(name)
    except Exception:  # no secrets file, or not running under Streamlit
        return None
    return None if value is None else str(value)


def _setting(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    if not value:
        value = (_streamlit_secret(name) or "").strip()
    return value or default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    backend = _setting("TIMEWISE_DATABASE", "sqlite").lower()
    if backend not in SUPPORTED_BACKENDS:
        raise ConfigurationError(
            f"TIMEWISE_DATABASE must be one of {SUPPORTED_BACKENDS}, got {backend!r}."
        )

    bigquery_project = _setting("TIMEWISE_BIGQUERY_PROJECT")
    cookie_secret = _setting("TIMEWISE_COOKIE_SECRET")
    if backend == "bigquery":
        if not bigquery_project:
            raise ConfigurationError(
                "TIMEWISE_BIGQUERY_PROJECT is required when TIMEWISE_DATABASE=bigquery."
            )
        if not cookie_secret:
            raise ConfigurationError(
                "TIMEWISE_COOKIE_SECRET is required when TIMEWISE_DATABASE=bigquery."
            )

    sqlite_path = Path(_setting("TIMEWISE_SQLITE_PATH", "data/timewise.db"))
    if not sqlite_path.is_absolute():
        sqlite_path = PROJECT_ROOT / sqlite_path

    return Settings(
        database_backend=backend,
        sqlite_path=sqlite_path,
        bigquery_project=bigquery_project,
        bigquery_dataset=_setting("TIMEWISE_BIGQUERY_DATASET", "timewise"),
        gemini_api_key=_setting("GEMINI_API_KEY"),
        gemini_model=_setting("GEMINI_MODEL", "gemini-flash-latest"),
        cookie_secret=cookie_secret or LOCAL_COOKIE_SECRET,
    )
