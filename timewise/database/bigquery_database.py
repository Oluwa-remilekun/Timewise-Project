"""BigQuery backend used by the deployed application."""

from datetime import date, datetime
from typing import Any

from google.cloud import bigquery

from timewise.database.base import Database, Params, Row
from timewise.database.schema import TABLES


def _parameter_type(value: Any) -> str:
    # bool and datetime are checked first because they subclass int and date.
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    if isinstance(value, float):
        return "FLOAT64"
    if isinstance(value, str):
        return "STRING"
    if isinstance(value, datetime):
        return "DATETIME"
    if isinstance(value, date):
        return "DATE"
    raise TypeError(f"Unsupported query parameter type: {type(value).__name__}")


class BigQueryDatabase(Database):
    def __init__(self, project: str, dataset: str, client: bigquery.Client | None = None):
        self._project = project
        self._dataset = dataset
        self._client = client or bigquery.Client(project=project)

    def table(self, name: str) -> str:
        if name not in TABLES:
            raise KeyError(f"Unknown table: {name}")
        return f"`{self._project}.{self._dataset}.{name}`"

    def ensure_schema(self) -> None:
        dataset_id = f"{self._project}.{self._dataset}"
        self._client.create_dataset(dataset_id, exists_ok=True)
        for name, columns in TABLES.items():
            schema = [
                bigquery.SchemaField(column, kind, mode="REQUIRED")
                for column, kind in columns.items()
            ]
            table = bigquery.Table(f"{dataset_id}.{name}", schema=schema)
            self._client.create_table(table, exists_ok=True)

    def query(self, sql: str, params: Params | None = None) -> list[Row]:
        return [dict(row.items()) for row in self._run(sql, params)]

    def execute(self, sql: str, params: Params | None = None) -> None:
        self._run(sql, params)

    def _run(self, sql: str, params: Params | None):
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(name, _parameter_type(value), value)
                for name, value in (params or {}).items()
            ]
        )
        return self._client.query(sql, job_config=job_config).result()
