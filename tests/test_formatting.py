from datetime import datetime

import pytest

from timewise.ui.formatting import (
    format_date,
    format_datetime,
    format_repeat,
    format_time,
    greeting,
)


def test_date_and_time_formats_have_no_leading_zeros():
    moment = datetime(2026, 11, 4, 9, 5)
    assert format_time(moment) == "9:05 AM"
    assert format_date(moment) == "Wed, Nov 4"
    assert format_datetime(moment) == "Wed, Nov 4 at 9:05 AM"


@pytest.mark.parametrize(
    ("minutes", "expected"), [(0, "Once"), (60, "Every 1h"), (1500, "Every 25h")]
)
def test_format_repeat(minutes, expected):
    assert format_repeat(minutes) == expected


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(0, "Good morning"), (11, "Good morning"), (12, "Good afternoon"), (18, "Good evening")],
)
def test_greeting_follows_the_time_of_day(hour, expected):
    assert greeting(datetime(2026, 11, 14, hour)) == expected
