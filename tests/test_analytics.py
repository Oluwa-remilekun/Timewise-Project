from datetime import date

import pytest

from timewise.analytics import (
    category_shares,
    day_verdict,
    fill_daily_trend,
    format_duration,
    logging_streak,
    percentage,
)

TODAY = date(2026, 11, 14)


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(0, "0m"), (45, "45m"), (60, "1h"), (125, "2h 5m"), (1440, "24h")],
)
def test_format_duration(minutes, expected):
    assert format_duration(minutes) == expected


def test_percentage_rounds_and_handles_zero_total():
    assert percentage(1, 3) == 33
    assert percentage(2, 3) == 67
    assert percentage(5, 0) == 0


def test_category_shares():
    shares = category_shares({"Productive": 90, "Unproductive": 30, "Fun": 0})
    assert shares == {"Productive": 75, "Unproductive": 25, "Fun": 0}


def test_category_shares_with_no_time_logged():
    assert category_shares({"Productive": 0, "Fun": 0}) == {"Productive": 0, "Fun": 0}


def test_fill_daily_trend_adds_missing_days_and_categories():
    logged = {date(2026, 11, 2): {"Productive": 60}}
    trend = fill_daily_trend(logged, date(2026, 11, 1), date(2026, 11, 3))
    assert list(trend) == [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3)]
    assert trend[date(2026, 11, 1)] == {"Productive": 0, "Unproductive": 0, "Fun": 0}
    assert trend[date(2026, 11, 2)] == {"Productive": 60, "Unproductive": 0, "Fun": 0}


def days_ago(*offsets):
    return {date.fromordinal(TODAY.toordinal() - offset) for offset in offsets}


@pytest.mark.parametrize(
    ("logged_days", "expected"),
    [
        (set(), 0),
        (days_ago(0), 1),
        (days_ago(0, 1, 2), 3),
        (days_ago(1, 2), 2),
        (days_ago(0, 2, 3), 1),
        (days_ago(2, 3), 0),
    ],
)
def test_logging_streak_counts_consecutive_days(logged_days, expected):
    assert logging_streak(logged_days, TODAY) == expected


@pytest.mark.parametrize(
    ("summary", "title"),
    [
        ({"Productive": 90, "Unproductive": 30, "Fun": 30}, "Locked in"),
        ({"Productive": 30, "Unproductive": 90, "Fun": 30}, "Drifting"),
        ({"Productive": 30, "Unproductive": 20, "Fun": 100}, "Play day"),
        ({"Productive": 50, "Unproductive": 40, "Fun": 40}, "Balanced day"),
    ],
)
def test_day_verdict(summary, title):
    assert day_verdict(summary).title == title


def test_day_verdict_is_none_when_nothing_is_logged():
    assert day_verdict({"Productive": 0, "Unproductive": 0, "Fun": 0}) is None
