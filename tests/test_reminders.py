from datetime import datetime

import pytest

from timewise.errors import ValidationError
from timewise.models import Reminder
from timewise.repositories import reminders

NINE = datetime(2026, 11, 14, 9, 0)
NOON = datetime(2026, 11, 14, 12, 0)


def test_add_and_list_reminders_soonest_first(user):
    reminders.add_reminder(user.id, "Lunch", "Event", NOON)
    reminders.add_reminder(user.id, "Essay", "Task", NINE, 60)

    listed = reminders.list_reminders(user.id)

    assert [reminder.title for reminder in listed] == ["Essay", "Lunch"]
    assert listed[0].is_repeating is True
    assert listed[1].is_repeating is False


def test_update_reminder(user):
    reminder = reminders.add_reminder(user.id, "Essay", "Task", NINE)
    reminders.update_reminder(user.id, reminder.id, NOON, 1440)

    updated = reminders.list_reminders(user.id)[0]

    assert (updated.remind_at, updated.repeat_interval_minutes) == (NOON, 1440)


def test_delete_reminder_requires_owner(user):
    reminder = reminders.add_reminder(user.id, "Essay", "Task", NINE)
    reminders.delete_reminder("someone-else", reminder.id)
    assert len(reminders.list_reminders(user.id)) == 1
    reminders.delete_reminder(user.id, reminder.id)
    assert reminders.list_reminders(user.id) == []


@pytest.mark.parametrize(
    ("title", "source_type", "interval"),
    [("", "Task", 0), ("Essay", "Email", 0), ("Essay", "Task", -5)],
)
def test_add_reminder_rejects_invalid_input(user, title, source_type, interval):
    with pytest.raises(ValidationError):
        reminders.add_reminder(user.id, title, source_type, NINE, interval)


def make_reminder(remind_at, interval):
    return Reminder("id", "Essay", "Task", remind_at, interval)


def test_next_occurrence_is_none_for_one_off_reminders():
    assert reminders.next_occurrence(make_reminder(NINE, 0), NOON) is None


def test_next_occurrence_skips_every_missed_interval():
    # Hourly from 9:00, checked at 12:00 -> 13:00, not 10:00.
    upcoming = reminders.next_occurrence(make_reminder(NINE, 60), NOON)
    assert upcoming == datetime(2026, 11, 14, 13, 0)


def test_next_occurrence_between_intervals():
    upcoming = reminders.next_occurrence(make_reminder(NINE, 60), datetime(2026, 11, 14, 9, 30))
    assert upcoming == datetime(2026, 11, 14, 10, 0)


def test_next_occurrence_keeps_a_future_time():
    assert reminders.next_occurrence(make_reminder(NOON, 60), NINE) == NOON


def test_acknowledging_a_one_off_reminder_removes_it(user):
    reminder = reminders.add_reminder(user.id, "Essay", "Task", NINE)
    reminders.acknowledge_reminder(user.id, reminder, NOON)
    assert reminders.list_reminders(user.id) == []


def test_acknowledging_a_repeating_reminder_reschedules_it(user):
    reminder = reminders.add_reminder(user.id, "Stretch", "Task", NINE, 1440)
    reminders.acknowledge_reminder(user.id, reminder, NOON)

    rescheduled = reminders.list_reminders(user.id)[0]

    assert rescheduled.remind_at == datetime(2026, 11, 15, 9, 0)
    assert rescheduled.repeat_interval_minutes == 1440
