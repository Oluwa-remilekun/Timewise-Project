"""Banner listing reminders whose time has arrived."""

from datetime import datetime

import streamlit as st

from timewise.models import Reminder
from timewise.repositories import reminders
from timewise.ui import session
from timewise.ui.formatting import format_datetime


def split_due(
    all_reminders: list[Reminder], now: datetime
) -> tuple[list[Reminder], list[Reminder]]:
    """Split reminders into (due, upcoming) relative to ``now``."""
    due = [reminder for reminder in all_reminders if reminder.remind_at <= now]
    upcoming = [reminder for reminder in all_reminders if reminder.remind_at > now]
    return due, upcoming


def render_due_reminders(due: list[Reminder], key_prefix: str) -> None:
    for reminder in due:
        message, action = st.columns([5, 1], vertical_alignment="center")
        message.warning(
            f"**{reminder.title}** was due {format_datetime(reminder.remind_at)}",
            icon=":material/notifications_active:",
        )
        if action.button("Dismiss", key=f"{key_prefix}_dismiss_{reminder.id}", width="stretch"):
            reminders.acknowledge_reminder(session.current_user().id, reminder, session.local_now())
            st.rerun()
