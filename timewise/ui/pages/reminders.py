"""Reminders page: schedule reminders for calendar events and to-do tasks."""

from datetime import datetime, time, timedelta

import streamlit as st

from timewise.constants import REMINDER_SOURCE_TYPES, REPEAT_INTERVALS
from timewise.errors import ValidationError
from timewise.models import Reminder
from timewise.repositories import events, reminders, tasks
from timewise.ui import session
from timewise.ui.components.due_reminders import render_due_reminders, split_due
from timewise.ui.components.page_header import render_page_header
from timewise.ui.formatting import format_date, format_datetime, format_repeat

_CUSTOM_REPEAT = "Custom"
_MAX_REPEAT_MINUTES = 365 * 24 * 60
_EVENT_LEAD_TIME = timedelta(minutes=30)
_TASK_REMINDER_TIME = time(hour=9)
_FILTERS = ("All", *REMINDER_SOURCE_TYPES)
_SORT_OPTIONS = ("Soonest first", "A to Z")
_SOURCE_BADGE_COLORS = {"Event": "orange", "Task": "blue"}


def _repeat_interval_input(current_minutes: int, key: str) -> int:
    labels = [*REPEAT_INTERVALS, _CUSTOM_REPEAT]
    current_label = next(
        (label for label, minutes in REPEAT_INTERVALS.items() if minutes == current_minutes),
        _CUSTOM_REPEAT,
    )
    choice = st.selectbox("Repeat", labels, index=labels.index(current_label), key=f"{key}_repeat")
    if choice != _CUSTOM_REPEAT:
        return REPEAT_INTERVALS[choice]
    return st.number_input(
        "Repeat every (minutes)",
        min_value=1,
        max_value=_MAX_REPEAT_MINUTES,
        value=max(current_minutes, 30),
        key=f"{key}_custom_minutes",
    )


def _reminder_candidates(source_type: str, now: datetime) -> dict[str, tuple[str, datetime]]:
    """Map a display label to (title, suggested reminder time) for each open item."""
    user_id = session.current_user().id
    if source_type == "Event":
        return {
            f"{event.title} ({format_datetime(event.starts_at)})": (
                event.title,
                max(event.starts_at - _EVENT_LEAD_TIME, now),
            )
            for event in events.list_upcoming_events(user_id, now)
        }
    return {
        f"{task.title} (due {format_date(task.due_date)})": (
            task.title,
            max(datetime.combine(task.due_date, _TASK_REMINDER_TIME), now),
        )
        for task in tasks.list_tasks(user_id)
        if not task.is_completed
    }


@st.dialog("Add a reminder")
def _add_reminder_dialog() -> None:
    now = session.local_now()
    source_type = st.segmented_control(
        "Remind me about", REMINDER_SOURCE_TYPES, default="Event", required=True
    )
    candidates = _reminder_candidates(source_type, now)
    if not candidates:
        missing = "upcoming events" if source_type == "Event" else "open tasks"
        st.info(f"You have no {missing} yet. Add one first, then set a reminder for it.")
        return

    label = st.selectbox(source_type, list(candidates))
    title, suggested_time = candidates[label]
    remind_at = st.datetime_input(
        "Remind me at", value=suggested_time, format="MM/DD/YYYY", key=f"remind_at_{label}"
    )
    interval = _repeat_interval_input(0, key="new_reminder")

    if st.button("Add reminder", type="primary", width="stretch"):
        if remind_at is None:
            st.error("Choose when to be reminded.")
            return
        try:
            reminders.add_reminder(
                session.current_user().id, title, source_type, remind_at, interval
            )
        except ValidationError as error:
            st.error(str(error))
        else:
            session.flash("Reminder added 🔔")
            st.rerun()


@st.dialog("Edit reminder")
def _edit_reminder_dialog(reminder: Reminder) -> None:
    st.markdown(f"**{reminder.title}**")
    remind_at = st.datetime_input(
        "Remind me at",
        value=reminder.remind_at,
        format="MM/DD/YYYY",
        key=f"edit_remind_at_{reminder.id}",
    )
    interval = _repeat_interval_input(reminder.repeat_interval_minutes, key=f"edit_{reminder.id}")

    user_id = session.current_user().id
    save, delete = st.columns(2)
    if save.button("Save", type="primary", width="stretch"):
        if remind_at is None:
            st.error("Choose when to be reminded.")
            return
        reminders.update_reminder(user_id, reminder.id, remind_at, interval)
        session.flash("Reminder updated.")
        st.rerun()
    if delete.button("Delete", width="stretch"):
        reminders.delete_reminder(user_id, reminder.id)
        session.flash("Reminder deleted.")
        st.rerun()


def _render_reminder(reminder: Reminder) -> Reminder | None:
    """Render one reminder card and return the reminder if its edit button was clicked."""
    with st.container(border=True, key=f"card-reminder-{reminder.id}"):
        badge, title, schedule, edit = st.columns([1, 4, 4, 1], vertical_alignment="center")
        badge.badge(reminder.source_type, color=_SOURCE_BADGE_COLORS[reminder.source_type])
        title.markdown(f"**{reminder.title}**")
        schedule.caption(
            f"{format_datetime(reminder.remind_at)} · "
            f"{format_repeat(reminder.repeat_interval_minutes)}"
        )
        clicked = edit.button(
            "",
            icon=":material/edit:",
            key=f"edit_reminder_{reminder.id}",
            help="Edit this reminder",
            type="tertiary",
        )
    return reminder if clicked else None


def render_reminders_page() -> None:
    user = session.current_user()
    now = session.local_now()
    all_reminders = reminders.list_reminders(user.id)
    due, _ = split_due(all_reminders, now)

    render_page_header("Reminders", "Nudges for the events and tasks you can't afford to miss.")
    add_column, filter_column, sort_column = st.columns([1, 2, 1], vertical_alignment="bottom")
    add_clicked = add_column.button("Add reminder", type="primary", icon=":material/add:")
    selected_filter = filter_column.segmented_control(
        "Show", _FILTERS, default="All", key="reminder_filter", required=True
    )
    sort_order = sort_column.selectbox("Sort by", _SORT_OPTIONS, key="reminder_sort")

    render_due_reminders(due, key_prefix="reminders")

    visible = [
        reminder
        for reminder in all_reminders
        if selected_filter == "All" or reminder.source_type == selected_filter
    ]
    if sort_order == "A to Z":
        visible.sort(key=lambda reminder: reminder.title.lower())

    if not visible:
        st.info("No reminders yet. Add one for an upcoming event or an open task.", icon="🔕")

    to_edit = None
    for reminder in visible:
        to_edit = _render_reminder(reminder) or to_edit

    if add_clicked:
        _add_reminder_dialog()
    elif to_edit:
        _edit_reminder_dialog(to_edit)
