"""Shared fixtures: every test runs against a fresh SQLite database."""

import pytest

from timewise import config, database
from timewise.auth import passwords


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMEWISE_DATABASE", "sqlite")
    monkeypatch.setenv("TIMEWISE_SQLITE_PATH", str(tmp_path / "timewise.db"))
    monkeypatch.setenv("TIMEWISE_COOKIE_SECRET", "test-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr(config, "_streamlit_secret", lambda name: None)
    monkeypatch.setattr(passwords, "_ITERATIONS", 1_000)
    config.get_settings.cache_clear()
    database.get_database.cache_clear()
    yield
    config.get_settings.cache_clear()
    database.get_database.cache_clear()


@pytest.fixture
def user():
    from timewise.auth import accounts

    account, _ = accounts.register("Remi Adeshina", "remi", "correct-horse")
    return account
