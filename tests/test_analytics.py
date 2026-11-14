from datetime import date

import pytest

from timewise.analytics import category_shares, fill_daily_trend, format_duration, percentage


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
