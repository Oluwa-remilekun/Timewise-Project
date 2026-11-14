"""SQLite backend: a zero-setup local file used for development and tests."""

import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from typing import Any

from timewise.database.base import Database, Params, Row
from timewise.database.schema import TABLES

_COLUMN_TYPES = {
    "STRING": "TEXT",
    "INT64": "INTEGER",
    "BOOL": "BOOLEAN",
    "DATE": "DATE",
    "DATETIME": "DATETIME",
}

sqlite3.register_converter("DATE", lambda raw: date.fromisoformat(raw.decode()))
sqlite3.register_converter("DATETIME", lambda raw: datetime.fromisoformat(raw.decode()))
sqlite3.register_converter("BOOLEAN", lambda raw: raw != b"0")


def _to_sqlite_value(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (str, int, float)):
        return value
    raise TypeError(f"Unsupported query parameter type: {type(value).__name__}")


class SQLiteDatabase(Database):
    def __init__(self, path: Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def table(self, name: str) -> str:
        if name not in TABLES:
            raise KeyError(f"Unknown table: {name}")
        return f'"{name}"'

    def ensure_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            for name, columns in TABLES.items():
                column_sql = ", ".join(
                    f'"{column}" {_COLUMN_TYPES[kind]} NOT NULL' for column, kind in columns.items()
                )
                connection.execute(f"CREATE TABLE IF NOT EXISTS {self.table(name)} ({column_sql})")

    def query(self, sql: str, params: Params | None = None) -> list[Row]:
        with closing(self._connect()) as connection:
            return [dict(row) for row in connection.execute(sql, self._bind(params))]

    def execute(self, sql: str, params: Params | None = None) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(sql, self._bind(params))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, detect_types=sqlite3.PARSE_DECLTYPES)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _bind(params: Params | None) -> dict[str, Any]:
        return {name: _to_sqlite_value(value) for name, value in (params or {}).items()}
