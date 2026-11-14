import pytest

from timewise.config import LOCAL_COOKIE_SECRET, ConfigurationError, get_settings


def reload_settings():
    get_settings.cache_clear()
    return get_settings()


def test_defaults_to_sqlite_with_local_cookie_secret(monkeypatch):
    monkeypatch.delenv("TIMEWISE_DATABASE")
    monkeypatch.delenv("TIMEWISE_COOKIE_SECRET")
    settings = reload_settings()
    assert settings.database_backend == "sqlite"
    assert settings.cookie_secret == LOCAL_COOKIE_SECRET
    assert settings.gemini_model == "gemini-flash-latest"


def test_rejects_unknown_backend(monkeypatch):
    monkeypatch.setenv("TIMEWISE_DATABASE", "postgres")
    with pytest.raises(ConfigurationError, match="TIMEWISE_DATABASE"):
        reload_settings()


def test_bigquery_requires_project(monkeypatch):
    monkeypatch.setenv("TIMEWISE_DATABASE", "bigquery")
    with pytest.raises(ConfigurationError, match="TIMEWISE_BIGQUERY_PROJECT"):
        reload_settings()


def test_bigquery_requires_cookie_secret(monkeypatch):
    monkeypatch.setenv("TIMEWISE_DATABASE", "bigquery")
    monkeypatch.setenv("TIMEWISE_BIGQUERY_PROJECT", "my-project")
    monkeypatch.delenv("TIMEWISE_COOKIE_SECRET")
    with pytest.raises(ConfigurationError, match="TIMEWISE_COOKIE_SECRET"):
        reload_settings()


def test_bigquery_settings(monkeypatch):
    monkeypatch.setenv("TIMEWISE_DATABASE", "BigQuery")
    monkeypatch.setenv("TIMEWISE_BIGQUERY_PROJECT", "my-project")
    settings = reload_settings()
    assert settings.database_backend == "bigquery"
    assert settings.bigquery_project == "my-project"
    assert settings.bigquery_dataset == "timewise"
