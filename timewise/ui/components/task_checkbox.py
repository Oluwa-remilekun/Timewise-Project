"""Checkbox that persists a task's completion state."""

import streamlit as st

from timewise.models import Task
from timewise.repositories import tasks
from timewise.ui import session


def _save_completion(task: Task, widget_key: str) -> None:
    user_id = session.current_user().id
    is_completed = st.session_state[widget_key]
    tasks.set_task_completion(user_id, task.id, is_completed)

    today = session.local_today()
    if is_completed and task.due_date == today:
        if all(item.is_completed for item in tasks.list_tasks_due_on(user_id, today)):
            session.flash("Everything due today is done! 🎉")
            session.celebrate()


def render_task_checkbox(task: Task, label: str, key_prefix: str) -> None:
    widget_key = f"{key_prefix}_{task.id}"
    st.checkbox(
        label,
        value=task.is_completed,
        key=widget_key,
        on_change=_save_completion,
        args=(task, widget_key),
    )
