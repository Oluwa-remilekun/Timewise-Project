"""Prompt templates. Each builder grounds the model in the user's own data."""

from datetime import date, datetime

from timewise.analytics import category_shares, format_duration
from timewise.models import Activity, Task

COACH_INSTRUCTION = (
    "You are TimeWise, a friendly productivity coach for students. "
    "Base every suggestion strictly on the data you are given and refer to the "
    "user's actual activities or tasks by name. Reply with 2-3 short bullet points "
    "in Markdown, under 90 words in total, with no greeting and no closing line."
)

EVENT_PARSER_INSTRUCTION = (
    "You extract one calendar event from a sentence. Reply with JSON only, using "
    'exactly these keys: {"title": string, "start": "YYYY-MM-DDTHH:MM", '
    '"end": "YYYY-MM-DDTHH:MM"}. Use 24-hour times. If no duration is given, '
    "make the event one hour long. Keep the title short."
)

_MAX_LISTED_ITEMS = 15


def activity_advice_prompt(summary: dict[str, int], activities: list[Activity], day: date) -> str:
    shares = category_shares(summary)
    totals = "\n".join(
        f"- {category}: {format_duration(minutes)} ({shares[category]}%)"
        for category, minutes in summary.items()
    )
    logged = "\n".join(
        f"- {activity.title}: {format_duration(activity.duration_minutes)} ({activity.category})"
        for activity in activities[:_MAX_LISTED_ITEMS]
    )
    return (
        f"Activity log for {day:%A, %B %d, %Y}.\n\n"
        f"Time per category:\n{totals}\n\n"
        f"Logged activities, longest first:\n{logged}\n\n"
        "Suggest how this person could spend their time better tomorrow."
    )


def daily_overview_prompt(tasks: list[Task], day: date) -> str:
    completed = [task.title for task in tasks if task.is_completed]
    pending = [f"{task.title} ({task.category})" for task in tasks if not task.is_completed]
    return (
        f"Tasks due on {day:%A, %B %d, %Y}.\n"
        f"Completed: {', '.join(completed) or 'none yet'}\n"
        f"Still pending: {', '.join(pending) or 'nothing'}\n\n"
        "Suggest how to get through the remaining tasks today."
    )


def task_priorities_prompt(tasks: list[Task], today: date) -> str:
    listed = "\n".join(
        f"- {task.title} (category: {task.category}, due: {task.due_date.isoformat()}"
        + (f", notes: {task.description}" if task.description else "")
        + ")"
        for task in tasks[:_MAX_LISTED_ITEMS]
    )
    return (
        f"Today is {today:%A, %B %d, %Y}. Open to-do items:\n{listed}\n\n"
        "Say which tasks to tackle first and why, then give one focus tip."
    )


def event_parser_prompt(text: str, now: datetime) -> str:
    return (
        f"The current date and time is {now:%A %Y-%m-%dT%H:%M}. Resolve relative "
        f'dates such as "tomorrow" against it.\n\nSentence: {text}'
    )
