from datetime import date

import pytest

from timewise.errors import ValidationError
from timewise.repositories import activities

TODAY = date(2026, 11, 14)
YESTERDAY = date(2026, 11, 13)


def test_add_and_list_activities_longest_first(user):
    activities.add_activity(user.id, "Read chapter 4", "Productive", 30, TODAY)
    activities.add_activity(user.id, "  Scrolling  ", "Unproductive", 90, TODAY)
    activities.add_activity(user.id, "Gym", "Fun", 60, YESTERDAY)

    logged = activities.list_activities(user.id, TODAY)

    assert [activity.title for activity in logged] == ["Scrolling", "Read chapter 4"]
    assert logged[0].duration_minutes == 90
    assert logged[0].activity_date == TODAY


def test_numeric_looking_titles_stay_text(user):
    activities.add_activity(user.id, "007", "Fun", 120, TODAY)
    assert activities.list_activities(user.id, TODAY)[0].title == "007"


def test_summarize_by_category_sums_minutes_and_includes_empty_categories(user):
    activities.add_activity(user.id, "Essay", "Productive", 45, TODAY)
    activities.add_activity(user.id, "Lab", "Productive", 75, TODAY)
    activities.add_activity(user.id, "Video games", "Fun", 30, TODAY)
    activities.add_activity(user.id, "Old entry", "Unproductive", 500, YESTERDAY)

    summary = activities.summarize_by_category(user.id, TODAY)

    assert summary == {"Productive": 120, "Unproductive": 0, "Fun": 30}


def test_summarize_by_day_groups_by_date_within_range(user):
    activities.add_activity(user.id, "Essay", "Productive", 45, TODAY)
    activities.add_activity(user.id, "Nap", "Fun", 20, YESTERDAY)
    activities.add_activity(user.id, "Ancient", "Fun", 20, date(2026, 10, 1))

    totals = activities.summarize_by_day(user.id, YESTERDAY, TODAY)

    assert totals == {TODAY: {"Productive": 45}, YESTERDAY: {"Fun": 20}}


def test_activities_are_private_to_their_owner(user):
    activities.add_activity(user.id, "Essay", "Productive", 45, TODAY)
    assert activities.list_activities("someone-else", TODAY) == []
    assert sum(activities.summarize_by_category("someone-else", TODAY).values()) == 0


def test_delete_activity_requires_owner(user):
    activity = activities.add_activity(user.id, "Essay", "Productive", 45, TODAY)

    activities.delete_activity("someone-else", activity.id)
    assert len(activities.list_activities(user.id, TODAY)) == 1

    activities.delete_activity(user.id, activity.id)
    assert activities.list_activities(user.id, TODAY) == []


@pytest.mark.parametrize(
    ("title", "category", "minutes"),
    [
        ("", "Productive", 30),
        ("   ", "Productive", 30),
        ("x" * 101, "Productive", 30),
        ("Essay", "Sleeping", 30),
        ("Essay", "Productive", 0),
        ("Essay", "Productive", 1441),
    ],
)
def test_add_activity_rejects_invalid_input(user, title, category, minutes):
    with pytest.raises(ValidationError):
        activities.add_activity(user.id, title, category, minutes, TODAY)
    assert activities.list_activities(user.id, TODAY) == []


def test_sql_injection_attempt_is_stored_as_text(user):
    title = "x'); DROP TABLE activities; --"
    activities.add_activity(user.id, title, "Fun", 5, TODAY)
    assert activities.list_activities(user.id, TODAY)[0].title == title
