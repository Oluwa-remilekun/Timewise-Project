from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from google.cloud import bigquery

from timewise.database import get_database
from timewise.database.bigquery_database import BigQueryDatabase
from timewise.database.schema import TABLES
from timewise.database.sqlite_database import SQLiteDatabase


def test_get_database_returns_a_ready_sqlite_backend():
    db = get_database()
    assert isinstance(db, SQLiteDatabase)
    assert get_database() is db
    for name in TABLES:
        assert db.query(f"SELECT * FROM {db.table(name)}") == []


def test_sqlite_schema_creation_is_idempotent_and_keeps_data():
    db = get_database()
    db.execute(
        f"INSERT INTO {db.table('events')} (id, user_id, title, starts_at, ends_at) "
        "VALUES (@id, @user_id, @title, @starts_at, @ends_at)",
        {
            "id": "1",
            "user_id": "u",
            "title": "Standup",
            "starts_at": datetime(2026, 11, 14, 9),
            "ends_at": datetime(2026, 11, 14, 10),
        },
    )
    db.ensure_schema()
    rows = db.query(f"SELECT * FROM {db.table('events')}")
    assert rows[0]["starts_at"] == datetime(2026, 11, 14, 9)


def test_sqlite_round_trips_every_supported_type():
    db = get_database()
    db.execute(
        f"INSERT INTO {db.table('tasks')} "
        "(id, user_id, title, description, category, due_date, is_completed, created_at) "
        "VALUES (@id, @user_id, @title, @description, @category, @due_date, @done, @now)",
        {
            "id": "1",
            "user_id": "u",
            "title": "Essay",
            "description": "",
            "category": "School",
            "due_date": date(2026, 11, 14),
            "done": True,
            "now": datetime(2026, 11, 14, 8, 30, 15),
        },
    )
    row = db.query(f"SELECT * FROM {db.table('tasks')} WHERE is_completed = @done", {"done": True})[
        0
    ]
    assert row["due_date"] == date(2026, 11, 14)
    assert row["is_completed"] is True
    assert row["created_at"] == datetime(2026, 11, 14, 8, 30, 15)
    assert row["description"] == ""


@pytest.mark.parametrize("backend", ["sqlite", "bigquery"])
def test_unknown_tables_are_rejected(backend):
    db = get_database() if backend == "sqlite" else BigQueryDatabase("p", "d", MagicMock())
    with pytest.raises(KeyError):
        db.table("users; DROP TABLE users")


def test_null_parameters_are_rejected():
    db = get_database()
    with pytest.raises(TypeError):
        db.query(f"SELECT * FROM {db.table('users')} WHERE id = @id", {"id": None})
    with pytest.raises(TypeError):
        BigQueryDatabase("p", "d", MagicMock()).query("SELECT @id", {"id": None})


@pytest.fixture
def bigquery_client():
    return MagicMock(spec=bigquery.Client)


def test_bigquery_table_reference_is_fully_qualified(bigquery_client):
    db = BigQueryDatabase("my-project", "timewise", bigquery_client)
    assert db.table("activities") == "`my-project.timewise.activities`"


def test_bigquery_ensure_schema_creates_dataset_and_all_tables(bigquery_client):
    BigQueryDatabase("my-project", "timewise", bigquery_client).ensure_schema()

    bigquery_client.create_dataset.assert_called_once_with("my-project.timewise", exists_ok=True)
    created = {
        call.args[0].table_id: call.args[0] for call in bigquery_client.create_table.call_args_list
    }
    assert set(created) == set(TABLES)
    assert all(
        call.kwargs == {"exists_ok": True} for call in bigquery_client.create_table.call_args_list
    )
    activity_fields = {field.name: field for field in created["activities"].schema}
    assert activity_fields["duration_minutes"].field_type == "INT64"
    assert activity_fields["activity_date"].field_type == "DATE"
    assert activity_fields["title"].mode == "REQUIRED"


def test_bigquery_query_sends_typed_named_parameters(bigquery_client):
    bigquery_client.query.return_value.result.return_value = [
        bigquery.Row(("Essay", 45), {"title": 0, "duration_minutes": 1})
    ]
    db = BigQueryDatabase("my-project", "timewise", bigquery_client)

    rows = db.query(
        "SELECT 1",
        {
            "user_id": "u1",
            "limit": 5,
            "done": False,
            "day": date(2026, 11, 14),
            "now": datetime(2026, 11, 14, 9, 0),
        },
    )

    assert rows == [{"title": "Essay", "duration_minutes": 45}]
    job_config = bigquery_client.query.call_args.kwargs["job_config"]
    parameters = {
        parameter.name: (parameter.type_, parameter.value)
        for parameter in job_config.query_parameters
    }
    assert parameters == {
        "user_id": ("STRING", "u1"),
        "limit": ("INT64", 5),
        "done": ("BOOL", False),
        "day": ("DATE", date(2026, 11, 14)),
        "now": ("DATETIME", datetime(2026, 11, 14, 9, 0)),
    }


def test_bigquery_execute_waits_for_the_job(bigquery_client):
    db = BigQueryDatabase("my-project", "timewise", bigquery_client)
    db.execute("DELETE FROM t WHERE id = @id", {"id": "1"})
    bigquery_client.query.return_value.result.assert_called_once_with()
