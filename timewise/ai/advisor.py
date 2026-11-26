"""Personalized guidance generated from a user's activities and tasks.

Every function returns usable advice: when Gemini is unavailable it falls back
to simple rule-based tips so the rest of the app keeps working.
"""

import logging
from dataclasses import dataclass
from datetime import date

from timewise.ai import prompts
from timewise.ai.client import AIUnavailableError, generate_text
from timewise.analytics import category_shares, format_duration
from timewise.models import Activity, Task

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Advice:
    text: str
    is_ai_generated: bool
    note: str = ""


def _advise(prompt: str, fallback: str) -> Advice:
    try:
        text = generate_text(prompt, system_instruction=prompts.COACH_INSTRUCTION)
    except AIUnavailableError as error:
        logger.warning("Falling back to rule-based advice: %s", error)
        return Advice(fallback, is_ai_generated=False, note=error.reason)
    return Advice(text, is_ai_generated=True)


def _as_bullets(tips: list[str]) -> str:
    return "\n".join(f"- {tip}" for tip in tips)


def _activity_tips(summary: dict[str, int], activities: list[Activity]) -> str:
    shares = category_shares(summary)
    tips = []
    if summary["Unproductive"] > summary["Productive"]:
        longest = max(
            (activity for activity in activities if activity.category == "Unproductive"),
            key=lambda activity: activity.duration_minutes,
        )
        tips.append(
            f"Unproductive time ({format_duration(summary['Unproductive'])}) outweighed "
            f'productive time. Try capping "{longest.title}" at half its '
            f"{format_duration(longest.duration_minutes)} tomorrow."
        )
    else:
        tips.append(
            f"{shares['Productive']}% of your tracked time was productive. "
            "Protect that block by scheduling it at the same time tomorrow."
        )
    if summary["Fun"] == 0:
        tips.append("No fun time logged. Plan a short break you enjoy to avoid burnout.")
    elif shares["Fun"] > 40:
        tips.append("Fun took over 40% of your day. Use it as a reward after focused work.")
    tips.append("Log activities as you go so tomorrow's breakdown stays accurate.")
    return _as_bullets(tips)


def activity_advice(summary: dict[str, int], activities: list[Activity], day: date) -> Advice:
    """Advice grounded in one day's activity log. Requires at least one activity."""
    return _advise(
        prompts.activity_advice_prompt(summary, activities, day),
        _activity_tips(summary, activities),
    )


def _overview_tips(tasks: list[Task]) -> str:
    pending = [task for task in tasks if not task.is_completed]
    if not tasks:
        return _as_bullets(
            [
                "Nothing is due today. Add one or two tasks to give the day a goal.",
                "Block out a focused hour for the task that matters most.",
            ]
        )
    if not pending:
        return _as_bullets(
            [
                "Everything due today is done. Nice work!",
                "Use the spare time to get ahead on tomorrow's tasks.",
            ]
        )
    urgent = next((task for task in pending if task.category == "Urgent"), pending[0])
    return _as_bullets(
        [
            f'Start with "{urgent.title}" while your energy is highest.',
            f"{len(pending)} of {len(tasks)} tasks remain. Work in 25-minute sprints "
            "with short breaks.",
        ]
    )


def daily_overview(tasks: list[Task], day: date) -> Advice:
    """A short plan for the tasks due on ``day``."""
    return _advise(prompts.daily_overview_prompt(tasks, day), _overview_tips(tasks))


def _priority_tips(tasks: list[Task]) -> str:
    ordered = sorted(tasks, key=lambda task: (task.category != "Urgent", task.due_date))
    tips = [
        f'{position}. "{task.title}" (due {task.due_date:%b %d})'
        for position, task in enumerate(ordered[:3], start=1)
    ]
    return (
        "Suggested order, urgent and earliest due first:\n\n"
        + "\n".join(tips)
        + "\n\nFinish one task completely before starting the next."
    )


def task_priorities(tasks: list[Task], today: date) -> Advice:
    """A suggested order for open tasks. Requires at least one task."""
    return _advise(prompts.task_priorities_prompt(tasks, today), _priority_tips(tasks))
