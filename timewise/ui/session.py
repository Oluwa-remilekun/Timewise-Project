"""Per-browser-session state: the signed-in user, local time and page links."""

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st

from timewise.auth import sessions as auth_sessions
from timewise.models import User
from timewise.ui import session_cookie

_DEFAULTS = {
    "user": None,
    "session_token": None,
    "cookie_checked": False,
    "auth_view": "login",
    "recovery_code": None,
    "flash_message": None,
    "celebrate": False,
}


def initialize() -> None:
    for key, value in _DEFAULTS.items():
        st.session_state.setdefault(key, value)


def is_signed_in() -> bool:
    return st.session_state.user is not None


def current_user() -> User:
    return st.session_state.user


def restore_from_cookie() -> None:
    """Sign the user back in from their session cookie, once per browser session."""
    if is_signed_in() or st.session_state.cookie_checked:
        return
    st.session_state.cookie_checked = True
    token = session_cookie.read_token()
    user = auth_sessions.resolve_session(token) if token else None
    if user:
        st.session_state.user = user
        st.session_state.session_token = token


def sign_in(user: User, remember: bool) -> None:
    token, _ = auth_sessions.start_session(user.id, remember)
    st.session_state.user = user
    st.session_state.session_token = token
    lifetime = auth_sessions.REMEMBERED_SESSION_LIFETIME
    session_cookie.queue_token(token, int(lifetime.total_seconds()) if remember else None)


def sign_out() -> None:
    auth_sessions.end_session(st.session_state.session_token)
    st.session_state.clear()
    initialize()
    st.session_state.cookie_checked = True
    session_cookie.queue_removal()


def flash(message: str) -> None:
    """Show a toast after the next rerun."""
    st.session_state.flash_message = message


def celebrate() -> None:
    """Release balloons after the next rerun."""
    st.session_state.celebrate = True


def show_flash() -> None:
    message = st.session_state.flash_message
    if message:
        st.session_state.flash_message = None
        st.toast(message)
    if st.session_state.celebrate:
        st.session_state.celebrate = False
        st.balloons()


def local_now() -> datetime:
    """Current time in the visitor's time zone, as a naive datetime."""
    try:
        zone = ZoneInfo(st.context.timezone) if st.context.timezone else None
    except (ZoneInfoNotFoundError, ValueError):
        zone = None
    return datetime.now(zone).replace(tzinfo=None, second=0, microsecond=0)


def local_today() -> date:
    return local_now().date()


def set_pages(pages: dict) -> None:
    st.session_state["_pages"] = pages


def page(name: str):
    """Return a registered page for use with ``st.page_link``."""
    return st.session_state["_pages"][name]
