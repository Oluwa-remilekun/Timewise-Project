"""Activity log storage and aggregation."""

from datetime import date

from timewise.clock import utc_now
from timewise.constants import ACTIVITY_CATEGORIES, MAX_ACTIVITY_MINUTES
from timewise.database import get_database
from timewise.errors import ValidationError
from timewise.models import Activity
from timewise.repositories import new_id
from timewise.validation import clean_title, require_choice

_COLUMNS = "id, title, category, duration_minutes, activity_date"


def add_activity(
    user_id: str, title: str, category: str, duration_minutes: int, activity_date: date
) -> Activity:
    title = clean_title(title, "Activity title")
    require_choice(category, ACTIVITY_CATEGORIES, "Category")
    duration_minutes = int(duration_minutes)
    if not 1 <= duration_minutes <= MAX_ACTIVITY_MINUTES:
        raise ValidationError(f"Duration must be between 1 and {MAX_ACTIVITY_MINUTES} minutes.")

    activity = Activity(new_id(), title, category, duration_minutes, activity_date)
    db = get_database()
    db.execute(
        f"""
        INSERT INTO {db.table("activities")}
            (id, user_id, title, category, duration_minutes, activity_date, created_at)
        VALUES
            (@id, @user_id, @title, @category, @duration_minutes, @activity_date, @created_at)
        """,
        {
            "id": activity.id,
            "user_id": user_id,
            "title": activity.title,
            "category": activity.category,
            "duration_minutes": activity.duration_minutes,
            "activity_date": activity.activity_date,
            "created_at": utc_now(),
        },
    )
    return activity


def list_activities(user_id: str, activity_date: date) -> list[Activity]:
    db = get_database()
    rows = db.query(
        f"""
        SELECT {_COLUMNS}
        FROM {db.table("activities")}
        WHERE user_id = @user_id AND activity_date = @activity_date
        ORDER BY duration_minutes DESC, title
        """,
        {"user_id": user_id, "activity_date": activity_date},
    )
    return [Activity(**row) for row in rows]


def summarize_by_category(user_id: str, activity_date: date) -> dict[str, int]:
    """Return total minutes per category for one day, including empty categories."""
    db = get_database()
    rows = db.query(
        f"""
        SELECT category, SUM(duration_minutes) AS total_minutes
        FROM {db.table("activities")}
        WHERE user_id = @user_id AND activity_date = @activity_date
        GROUP BY category
        """,
        {"user_id": user_id, "activity_date": activity_date},
    )
    totals = {category: 0 for category in ACTIVITY_CATEGORIES}
    for row in rows:
        totals[row["category"]] = int(row["total_minutes"])
    return totals


def summarize_by_day(user_id: str, start_date: date, end_date: date) -> dict[date, dict[str, int]]:
    """Return total minutes per category for each day that has activity in the range."""
    db = get_database()
    rows = db.query(
        f"""
        SELECT activity_date, category, SUM(duration_minutes) AS total_minutes
        FROM {db.table("activities")}
        WHERE user_id = @user_id
          AND activity_date >= @start_date
          AND activity_date <= @end_date
        GROUP BY activity_date, category
        """,
        {"user_id": user_id, "start_date": start_date, "end_date": end_date},
    )
    totals: dict[date, dict[str, int]] = {}
    for row in rows:
        day_totals = totals.setdefault(row["activity_date"], {})
        day_totals[row["category"]] = int(row["total_minutes"])
    return totals


def delete_activity(user_id: str, activity_id: str) -> None:
    db = get_database()
    db.execute(
        f"DELETE FROM {db.table('activities')} WHERE id = @id AND user_id = @user_id",
        {"id": activity_id, "user_id": user_id},
    )
