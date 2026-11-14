"""Pure calculations behind the dashboard. No database or UI access."""

from datetime import date, timedelta

from timewise.constants import ACTIVITY_CATEGORIES


def format_duration(minutes: int) -> str:
    """Format minutes as a compact duration, for example ``2h 5m``."""
    hours, remainder = divmod(int(minutes), 60)
    if hours and remainder:
        return f"{hours}h {remainder}m"
    if hours:
        return f"{hours}h"
    return f"{remainder}m"


def percentage(part: int, whole: int) -> int:
    """Return ``part`` as a rounded percentage of ``whole`` (0 when ``whole`` is 0)."""
    if whole <= 0:
        return 0
    return round(100 * part / whole)


def category_shares(summary: dict[str, int]) -> dict[str, int]:
    """Return each category's percentage of the total tracked time."""
    total = sum(summary.values())
    return {category: percentage(minutes, total) for category, minutes in summary.items()}


def fill_daily_trend(
    totals_by_day: dict[date, dict[str, int]], start_date: date, end_date: date
) -> dict[date, dict[str, int]]:
    """Return one entry per day in the range, with zeros where nothing was logged."""
    trend: dict[date, dict[str, int]] = {}
    day = start_date
    while day <= end_date:
        logged = totals_by_day.get(day, {})
        trend[day] = {category: logged.get(category, 0) for category in ACTIVITY_CATEGORIES}
        day += timedelta(days=1)
    return trend
