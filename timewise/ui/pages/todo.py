"""To-do page: add, complete, delete and prioritize tasks."""

from datetime import date

import streamlit as st

from timewise.ai import advisor
from timewise.constants import (
    MAX_TITLE_LENGTH,
    TASK_CATEGORIES,
    TASK_CATEGORY_COLORS,
    TASK_CATEGORY_EMOJI,
)
from timewise.errors import ValidationError
from timewise.models import Task
from timewise.repositories import tasks
from timewise.ui import session
from timewise.ui.components.advice import render_advice
from timewise.ui.components.page_header import render_page_header
from timewise.ui.components.task_checkbox import render_task_checkbox
from timewise.ui.formatting import format_date

_FILTERS = ("Open", "Completed", "All")


def _category_label(category: str) -> str:
    return f"{TASK_CATEGORY_EMOJI[category]} {category}"


def _render_add_task_form(today: date) -> None:
    with st.form("add_task_form", clear_on_submit=True, border=False):
        title = st.text_input(
            "Task", placeholder="e.g. Submit lab report", max_chars=MAX_TITLE_LENGTH
        )
        description = st.text_area("Notes (optional)", height=80)
        category_column, date_column = st.columns(2)
        category = category_column.selectbox(
            "Category", TASK_CATEGORIES, format_func=_category_label
        )
        due_date = date_column.date_input("Due date", value=today, format="MM/DD/YYYY")
        submitted = st.form_submit_button("Add task", type="primary", icon=":material/add:")

    if submitted:
        try:
            tasks.add_task(session.current_user().id, title, category, due_date, description)
        except ValidationError as error:
            st.error(str(error))
        else:
            session.flash("Task added 📝")
            st.rerun()


def _due_label(task: Task, today: date) -> str:
    label = f"Due {format_date(task.due_date)}"
    if not task.is_completed and task.due_date < today:
        return f":red[{label} · overdue]"
    return label


def _render_task(task: Task, today: date) -> None:
    with st.container(border=True, key=f"card-task-{task.id}"):
        checkbox, remove = st.columns([5, 1], vertical_alignment="center")
        with checkbox:
            render_task_checkbox(task, task.title, key_prefix="todo_task")
        if remove.button(
            "",
            icon=":material/delete:",
            key=f"delete_task_{task.id}",
            help="Delete this task",
            type="tertiary",
        ):
            tasks.delete_task(session.current_user().id, task.id)
            session.flash("Task deleted.")
            st.rerun()
        st.caption(_due_label(task, today))
        if task.description:
            st.caption(task.description)


def render_todo_page() -> None:
    user = session.current_user()
    today = session.local_today()
    all_tasks = tasks.list_tasks(user.id)
    open_tasks = [task for task in all_tasks if not task.is_completed]
    completed_count = len(all_tasks) - len(open_tasks)

    render_page_header("To-do", "Plan the work, then check it off.")

    if all_tasks:
        st.progress(
            completed_count / len(all_tasks),
            text=f"✅ {completed_count} of {len(all_tasks)} tasks done",
        )

    add_column, advice_column = st.columns(2, gap="large")
    with add_column:
        st.subheader("New task")
        _render_add_task_form(today)
    with advice_column:
        st.subheader("What should I do first?")
        if open_tasks:
            render_advice(
                state_key="task_priorities",
                signature=(today, tuple(open_tasks)),
                generate=lambda: advisor.task_priorities(open_tasks, today),
                button_label="Prioritize my tasks",
            )
        else:
            st.caption("Add a task and TimeWise will suggest where to start.")

    st.divider()
    selected_filter = st.segmented_control(
        "Show", _FILTERS, default="Open", key="todo_filter", required=True
    )
    if selected_filter == "Open":
        visible = open_tasks
    elif selected_filter == "Completed":
        visible = [task for task in all_tasks if task.is_completed]
    else:
        visible = all_tasks

    if not visible:
        st.info("No tasks to show.", icon="🌱")
        return

    for column, category in zip(st.columns(len(TASK_CATEGORIES)), TASK_CATEGORIES, strict=True):
        with column:
            st.markdown(f"#### :{TASK_CATEGORY_COLORS[category]}[{_category_label(category)}]")
            for task in visible:
                if task.category == category:
                    _render_task(task, today)
