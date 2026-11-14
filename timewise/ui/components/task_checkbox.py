"""Checkbox that persists a task's completion state."""

import streamlit as st

from timewise.models import Task
from timewise.repositories import tasks
from timewise.ui import session


def _save_completion(task_id: str, widget_key: str) -> None:
    tasks.set_task_completion(session.current_user().id, task_id, st.session_state[widget_key])


def render_task_checkbox(task: Task, label: str, key_prefix: str) -> None:
    widget_key = f"{key_prefix}_{task.id}"
    st.checkbox(
        label,
        value=task.is_completed,
        key=widget_key,
        on_change=_save_completion,
        args=(task.id, widget_key),
    )
