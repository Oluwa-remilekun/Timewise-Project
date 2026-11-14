"""Home page: today's summary across activities, tasks and reminders."""

import streamlit as st

from timewise.ai import advisor
from timewise.analytics import category_shares, format_duration, percentage
from timewise.constants import TASK_CATEGORY_COLORS
from timewise.repositories import activities, reminders, tasks
from timewise.ui import charts, session
from timewise.ui.components.advice import render_advice
from timewise.ui.components.due_reminders import render_due_reminders, split_due
from timewise.ui.components.task_checkbox import render_task_checkbox
from timewise.ui.formatting import format_datetime

_UPCOMING_REMINDER_LIMIT = 3


def render_home_page() -> None:
    user = session.current_user()
    now = session.local_now()
    today = now.date()

    todays_tasks = tasks.list_tasks_due_on(user.id, today)
    summary = activities.summarize_by_category(user.id, today)
    due, upcoming = split_due(reminders.list_reminders(user.id), now)
    completed = sum(task.is_completed for task in todays_tasks)

    st.title(f"Welcome, {user.name.split()[0]}")
    st.caption(f"{today:%A, %B} {today.day}, {today.year}")

    tracked, productive, done, scheduled = st.columns(4)
    tracked.metric("Tracked today", format_duration(sum(summary.values())), border=True)
    productive.metric("Productive share", f"{category_shares(summary)['Productive']}%", border=True)
    done.metric("Tasks done today", f"{completed} of {len(todays_tasks)}", border=True)
    scheduled.metric("Upcoming reminders", len(upcoming), border=True)

    render_due_reminders(due, key_prefix="home")

    main, side = st.columns([3, 2], gap="large")

    with main:
        st.subheader("Today's tasks")
        if not todays_tasks:
            st.info("Nothing is due today. Add tasks on the To-do page.")
        for task in todays_tasks:
            color = TASK_CATEGORY_COLORS[task.category]
            render_task_checkbox(
                task, f"{task.title} :{color}-badge[{task.category}]", key_prefix="home_task"
            )
        st.page_link(session.page("todo"), label="Manage tasks", icon=":material/checklist:")

        st.subheader("Plan for today")
        render_advice(
            state_key="home_overview",
            signature=(today, tuple((task.id, task.is_completed) for task in todays_tasks)),
            generate=lambda: advisor.daily_overview(todays_tasks, today),
            button_label="Suggest a plan",
        )

    with side:
        st.subheader("Task completion")
        if todays_tasks:
            figure = charts.completion_donut(
                completed,
                len(todays_tasks),
                center_text=f"{percentage(completed, len(todays_tasks))}%",
            )
            st.plotly_chart(figure, key="home_completion_chart")
        else:
            st.info("No tasks to chart yet.")

        st.subheader("Upcoming reminders")
        if not upcoming:
            st.info("No upcoming reminders.")
        for reminder in upcoming[:_UPCOMING_REMINDER_LIMIT]:
            with st.container(border=True):
                st.markdown(f"**{reminder.title}**")
                st.caption(f"{format_datetime(reminder.remind_at)} · {reminder.source_type}")
        st.page_link(
            session.page("calendar"), label="Open calendar", icon=":material/calendar_month:"
        )
