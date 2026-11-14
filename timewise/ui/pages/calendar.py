"""Calendar page: view, create and edit events, with AI-assisted quick entry."""

from datetime import timedelta

import streamlit as st
from streamlit_calendar import calendar

from timewise.ai import client as ai_client
from timewise.ai.event_parser import EventDraft, parse_event
from timewise.constants import MAX_TITLE_LENGTH
from timewise.errors import ValidationError
from timewise.models import Event
from timewise.repositories import events
from timewise.ui import session

_VERSION_KEY = "calendar_version"
_CALENDAR_OPTIONS = {
    "initialView": "timeGridWeek",
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,timeGridDay",
    },
    "nowIndicator": True,
    "allDaySlot": False,
    "slotDuration": "00:30:00",
    "scrollTime": "08:00:00",
    "height": 650,
    "editable": False,
    "selectable": False,
}


def _reset_calendar() -> None:
    """Remount the calendar so a handled event click is not replayed on rerun."""
    st.session_state[_VERSION_KEY] = st.session_state.get(_VERSION_KEY, 0) + 1


def _close_dialog(message: str) -> None:
    session.flash(message)
    _reset_calendar()
    st.rerun()


@st.dialog("Event", on_dismiss=_reset_calendar)
def _event_dialog(event: Event | None = None, draft: EventDraft | None = None) -> None:
    source = event or draft
    if source:
        default_title, default_start, default_end = source.title, source.starts_at, source.ends_at
    else:
        default_title = ""
        default_start = session.local_now().replace(minute=0) + timedelta(hours=1)
        default_end = default_start + timedelta(hours=1)
    key = event.id if event else "new"

    title = st.text_input(
        "Title", value=default_title, max_chars=MAX_TITLE_LENGTH, key=f"event_title_{key}"
    )
    starts_at = st.datetime_input(
        "Starts", value=default_start, format="MM/DD/YYYY", key=f"event_start_{key}"
    )
    ends_at = st.datetime_input(
        "Ends", value=default_end, format="MM/DD/YYYY", key=f"event_end_{key}"
    )

    user_id = session.current_user().id
    save, delete = st.columns(2)
    if save.button("Save", type="primary", width="stretch", key=f"event_save_{key}"):
        if starts_at is None or ends_at is None:
            st.error("Start and end times are required.")
            return
        try:
            if event:
                events.update_event(user_id, event.id, title, starts_at, ends_at)
            else:
                events.add_event(user_id, title, starts_at, ends_at)
        except ValidationError as error:
            st.error(str(error))
        else:
            _close_dialog("Event saved.")
    if event and delete.button("Delete", width="stretch", key=f"event_delete_{key}"):
        events.delete_event(user_id, event.id)
        _close_dialog("Event deleted.")


def _parse_quick_event(text: str) -> EventDraft | None:
    if not text.strip():
        st.warning("Describe the event first, for example: Study group tomorrow at 2 PM.")
        return None
    if not ai_client.is_configured():
        st.error("Set GEMINI_API_KEY to create events with AI, or add the event manually.")
        return None
    try:
        with st.spinner("Reading your event..."):
            return parse_event(text, session.local_now())
    except ai_client.AIUnavailableError:
        st.error("That could not be turned into an event. Try rephrasing or add it manually.")
        return None


def render_calendar_page() -> None:
    user = session.current_user()
    st.title("Calendar")

    dialog_opened = False
    manual_column, quick_column = st.columns([1, 4], vertical_alignment="bottom")
    if manual_column.button("New event", type="primary", icon=":material/add:"):
        _event_dialog()
        dialog_opened = True
    with quick_column.form("quick_event_form", border=False):
        text_column, submit_column = st.columns([4, 1], vertical_alignment="bottom")
        quick_text = text_column.text_input(
            "Or describe it and let AI fill in the details",
            placeholder="e.g. Study group tomorrow at 2 PM for 90 minutes",
        )
        submitted = submit_column.form_submit_button(
            "Create with AI", icon=":material/auto_awesome:", width="stretch"
        )
    if submitted and not dialog_opened:
        draft = _parse_quick_event(quick_text)
        if draft:
            _event_dialog(draft=draft)
            dialog_opened = True

    calendar_state = calendar(
        events=[
            {
                "id": event.id,
                "title": event.title,
                "start": event.starts_at.isoformat(),
                "end": event.ends_at.isoformat(),
            }
            for event in events.list_events(user.id)
        ],
        options=_CALENDAR_OPTIONS,
        callbacks=["eventClick"],
        key=f"calendar_{st.session_state.get(_VERSION_KEY, 0)}",
    )

    if not dialog_opened and calendar_state.get("callback") == "eventClick":
        clicked = events.get_event(user.id, calendar_state["eventClick"]["event"]["id"])
        if clicked:
            _event_dialog(event=clicked)
