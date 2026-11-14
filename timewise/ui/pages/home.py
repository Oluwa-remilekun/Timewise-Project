"""Home page: today's summary across activities, tasks and reminders."""

from datetime import timedelta

import streamlit as st

from timewise.ai import advisor
from timewise.analytics import (
    category_shares,
    fill_daily_trend,
    format_duration,
    logging_streak,
    percentage,
)
from timewise.constants import ACTIVITY_CATEGORY_EMOJI, TASK_CATEGORY_COLORS
from timewise.repositories import activities, reminders, tasks
from timewise.ui import charts, session
from timewise.ui.components.advice import render_advice
from timewise.ui.components.due_reminders import render_due_reminders, split_due
from timewise.ui.components.page_header import render_page_header
from timewise.ui.components.task_checkbox import render_task_checkbox
from timewise.ui.formatting import format_datetime, greeting

_UPCOMING_REMINDER_LIMIT = 3
_HISTORY_DAYS = 60
_DAILY_NUDGES = (
    "New week, clean slate. Pick the one thing that matters most.",
    "Small steps still count. Log the first one.",
    "Halfway there. Protect an hour for deep work today.",
    "Momentum beats motivation. Keep the streak alive.",
    "Finish strong, then enjoy the weekend guilt-free.",
    "Rest is productive too. Plan something fun.",
    "A little planning today makes Monday easier.",
)


def _streak_line(streak: int) -> str:
    if streak == 0:
        return "✨ Log an activity today to start a streak."
    days = "day" if streak == 1 else "days"
    return f"🔥 **{streak} {days}** logging streak. Keep it going!"


def render_home_page() -> None:
    user = session.current_user()
    now = session.local_now()
    today = now.date()

    todays_tasks = tasks.list_tasks_due_on(user.id, today)
    history = activities.summarize_by_day(user.id, today - timedelta(days=_HISTORY_DAYS - 1), today)
    summary = fill_daily_trend(history, today, today)[today]
    shares = category_shares(summary)
    due, upcoming = split_due(reminders.list_reminders(user.id), now)
    completed = sum(task.is_completed for task in todays_tasks)

    render_page_header(
        f"{greeting(now)}, {user.name.split()[0]}",
        f"{today:%A, %B} {today.day} · {_DAILY_NUDGES[today.weekday()]}",
        _streak_line(logging_streak(history.keys(), today)),
    )

    tracked, productive, done, scheduled = st.columns(4)
    tracked.metric("⏱️ Tracked today", format_duration(sum(summary.values())), border=True)
    productive.metric("🎯 Productive share", f"{shares['Productive']}%", border=True)
    done.metric("✅ Tasks done today", f"{completed} of {len(todays_tasks)}", border=True)
    scheduled.metric("🔔 Upcoming reminders", len(upcoming), border=True)

    render_due_reminders(due, key_prefix="home")

    main, side = st.columns([3, 2], gap="large")

    with main:
        st.subheader("Today's tasks")
        if not todays_tasks:
            st.info("Nothing is due today. Add tasks on the To-do page.", icon="🌤️")
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

        st.subheader("Where today went")
        if sum(summary.values()) == 0:
            st.info("No time logged yet. Head to the Time Analyser to add some.", icon="⏳")
        for category, minutes in summary.items():
            st.progress(
                shares[category] / 100,
                text=f"{ACTIVITY_CATEGORY_EMOJI[category]} {category} · {format_duration(minutes)}",
            )
        st.page_link(
            session.page("analyser"), label="Open Time Analyser", icon=":material/monitoring:"
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
            st.info("No tasks to chart yet.", icon="📋")

        st.subheader("Upcoming reminders")
        if not upcoming:
            st.info("No upcoming reminders.", icon="🔕")
        for reminder in upcoming[:_UPCOMING_REMINDER_LIMIT]:
            with st.container(border=True, key=f"card-home-reminder-{reminder.id}"):
                st.markdown(f"🔔 **{reminder.title}**")
                st.caption(f"{format_datetime(reminder.remind_at)} · {reminder.source_type}")
        st.page_link(
            session.page("calendar"), label="Open calendar", icon=":material/calendar_month:"
        )
