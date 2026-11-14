from datetime import datetime

import pytest

from timewise.errors import ValidationError
from timewise.repositories import events

NINE = datetime(2026, 11, 14, 9, 0)
TEN = datetime(2026, 11, 14, 10, 0)
NOON = datetime(2026, 11, 14, 12, 0)


def test_add_and_get_event(user):
    event = events.add_event(user.id, "Standup", NINE, TEN)
    assert events.get_event(user.id, event.id) == event
    assert events.get_event("someone-else", event.id) is None


def test_list_events_in_start_order(user):
    events.add_event(user.id, "Lunch", NOON, NOON.replace(hour=13))
    events.add_event(user.id, "Standup", NINE, TEN)
    assert [event.title for event in events.list_events(user.id)] == ["Standup", "Lunch"]


def test_update_event(user):
    event = events.add_event(user.id, "Standup", NINE, TEN)
    events.update_event(user.id, event.id, "Planning", TEN, NOON)

    updated = events.get_event(user.id, event.id)

    assert (updated.title, updated.starts_at, updated.ends_at) == ("Planning", TEN, NOON)


def test_delete_event(user):
    event = events.add_event(user.id, "Standup", NINE, TEN)
    events.delete_event(user.id, event.id)
    assert events.list_events(user.id) == []


def test_upcoming_events_exclude_finished_ones(user):
    events.add_event(user.id, "Finished", NINE, TEN)
    events.add_event(user.id, "In progress", TEN, NOON)
    upcoming = events.list_upcoming_events(user.id, now=datetime(2026, 11, 14, 11, 0))
    assert [event.title for event in upcoming] == ["In progress"]


@pytest.mark.parametrize(("starts_at", "ends_at"), [(TEN, NINE), (TEN, TEN)])
def test_event_must_end_after_it_starts(user, starts_at, ends_at):
    with pytest.raises(ValidationError, match="end after"):
        events.add_event(user.id, "Backwards", starts_at, ends_at)


def test_update_rejects_invalid_times_and_keeps_original(user):
    event = events.add_event(user.id, "Standup", NINE, TEN)
    with pytest.raises(ValidationError):
        events.update_event(user.id, event.id, "Standup", TEN, NINE)
    assert events.get_event(user.id, event.id) == event
