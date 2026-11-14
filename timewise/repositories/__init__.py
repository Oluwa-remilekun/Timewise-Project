"""Data access functions, one module per table."""

from uuid import uuid4


def new_id() -> str:
    return uuid4().hex
