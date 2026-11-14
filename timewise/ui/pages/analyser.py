"""Time Analyser page: log activities, see the breakdown, get AI suggestions."""

from datetime import date, timedelta

import streamlit as st

from timewise.ai import advisor
from timewise.analytics import category_shares, day_verdict, fill_daily_trend, format_duration
from timewise.constants import (
    ACTIVITY_CATEGORIES,
    ACTIVITY_CATEGORY_EMOJI,
    MAX_ACTIVITY_MINUTES,
    MAX_TITLE_LENGTH,
)
from timewise.errors import ValidationError
from timewise.models import Activity
from timewise.repositories import activities
from timewise.ui import charts, session
from timewise.ui.components.advice import render_advice
from timewise.ui.components.page_header import render_page_header

_TREND_DAYS = 7
_CATEGORY_BADGE_COLORS = {"Productive": "green", "Unproductive": "red", "Fun": "orange"}


def _category_label(category: str) -> str:
    return f"{ACTIVITY_CATEGORY_EMOJI[category]} {category}"


@st.dialog("Log an activity")
def _log_activity_dialog(default_date: date) -> None:
    title = st.text_input(
        "What did you do?", placeholder="e.g. Studied for calculus", max_chars=MAX_TITLE_LENGTH
    )
    duration = st.number_input(
        "Minutes spent", min_value=1, max_value=MAX_ACTIVITY_MINUTES, value=30, step=5
    )
    category = st.segmented_control(
        "Category",
        ACTIVITY_CATEGORIES,
        default=ACTIVITY_CATEGORIES[0],
        format_func=_category_label,
        required=True,
    )
    activity_date = st.date_input(
        "Date", value=default_date, max_value=session.local_today(), format="MM/DD/YYYY"
    )

    if st.button("Save activity", type="primary", width="stretch"):
        try:
            activities.add_activity(
                session.current_user().id, title, category, duration, activity_date
            )
        except ValidationError as error:
            st.error(str(error))
        else:
            session.flash("Activity logged ⏱️")
            st.rerun()


def _render_activity_list(logged: list[Activity]) -> None:
    for activity in logged:
        with st.container(border=True, key=f"card-activity-{activity.id}"):
            title, category, duration, remove = st.columns(
                [4, 4, 2, 1], vertical_alignment="center"
            )
            title.markdown(f"**{activity.title}**")
            category.badge(
                _category_label(activity.category),
                color=_CATEGORY_BADGE_COLORS[activity.category],
            )
            duration.write(format_duration(activity.duration_minutes))
            if remove.button(
                "",
                icon=":material/delete:",
                key=f"delete_activity_{activity.id}",
                help="Delete this activity",
                type="tertiary",
            ):
                activities.delete_activity(session.current_user().id, activity.id)
                session.flash("Activity deleted.")
                st.rerun()


def render_analyser_page() -> None:
    user = session.current_user()
    today = session.local_today()

    render_page_header("Time Analyser", "Log what you did and see where the day actually went.")

    date_column, action_column = st.columns([1, 3], vertical_alignment="bottom")
    selected_date = date_column.date_input("Day", value=today, max_value=today, format="MM/DD/YYYY")
    if action_column.button("Log activity", type="primary", icon=":material/add:"):
        _log_activity_dialog(selected_date)

    logged = activities.list_activities(user.id, selected_date)
    summary = activities.summarize_by_category(user.id, selected_date)
    shares = category_shares(summary)

    verdict = day_verdict(summary)
    if verdict:
        with st.container(key="verdict"):
            st.markdown(f"### {verdict.emoji} {verdict.title}")
            st.markdown(verdict.detail)

    metric_columns = st.columns(len(ACTIVITY_CATEGORIES) + 1)
    metric_columns[0].metric("⏱️ Total tracked", format_duration(sum(summary.values())), border=True)
    for column, category in zip(metric_columns[1:], ACTIVITY_CATEGORIES, strict=True):
        column.metric(
            _category_label(category),
            format_duration(summary[category]),
            f"{shares[category]}% of day",
            delta_color="off",
            delta_arrow="off",
            border=True,
        )

    breakdown, trend = st.columns(2, gap="large")
    with breakdown:
        st.subheader("Time breakdown")
        if logged:
            st.plotly_chart(charts.category_donut(summary), key="category_chart")
        else:
            st.info("No activities logged for this day yet.", icon="⏳")
    with trend:
        st.subheader(f"Last {_TREND_DAYS} days")
        trend_start = selected_date - timedelta(days=_TREND_DAYS - 1)
        totals = activities.summarize_by_day(user.id, trend_start, selected_date)
        if totals:
            figure = charts.daily_trend_bars(fill_daily_trend(totals, trend_start, selected_date))
            st.plotly_chart(figure, key="trend_chart")
        else:
            st.info("Log activities to see your weekly trend.", icon="📈")

    log_column, advice_column = st.columns(2, gap="large")
    with log_column:
        st.subheader("Activities")
        if logged:
            _render_activity_list(logged)
        else:
            st.caption("Nothing logged.")
    with advice_column:
        st.subheader("AI suggestions")
        if logged:
            render_advice(
                state_key="activity_advice",
                signature=(selected_date, tuple(logged)),
                generate=lambda: advisor.activity_advice(summary, logged, selected_date),
                button_label="Get suggestions",
            )
        else:
            st.caption("Log at least one activity to get personalized suggestions.")
