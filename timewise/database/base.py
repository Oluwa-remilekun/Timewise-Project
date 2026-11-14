"""The interface every storage backend implements.

Queries are written once in a SQL subset both backends understand: named
``@parameters``, no backend-specific functions, and table names obtained from
``Database.table``. Parameter values may be str, int, float, bool, date or
datetime; NULL is not supported, so every column has a non-null default.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

Params = Mapping[str, Any]
Row = dict[str, Any]


class Database(ABC):
    @abstractmethod
    def table(self, name: str) -> str:
        """Return the fully qualified, quoted reference for a schema table."""

    @abstractmethod
    def ensure_schema(self) -> None:
        """Create any missing tables. Safe to call repeatedly."""

    @abstractmethod
    def query(self, sql: str, params: Params | None = None) -> list[Row]:
        """Run a SELECT statement and return its rows."""

    @abstractmethod
    def execute(self, sql: str, params: Params | None = None) -> None:
        """Run an INSERT, UPDATE or DELETE statement."""
