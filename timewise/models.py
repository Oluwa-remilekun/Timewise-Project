"""Plain data records returned by the repositories."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class User:
    id: str
    name: str
    username: str


@dataclass(frozen=True)
class Activity:
    id: str
    title: str
    category: str
    duration_minutes: int
    activity_date: date


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    description: str
    category: str
    due_date: date
    is_completed: bool


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class Reminder:
    id: str
    title: str
    source_type: str
    remind_at: datetime
    repeat_interval_minutes: int

    @property
    def is_repeating(self) -> bool:
        return self.repeat_interval_minutes > 0
