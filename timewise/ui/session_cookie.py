"""Encrypted browser cookie that keeps a user signed in between visits.

The cookie holds a session token encrypted with a key derived from
TIMEWISE_COOKIE_SECRET. Streamlit can read request cookies but cannot set them,
so writes are queued and applied by a small script on the next render.
"""

import base64
import hashlib
import json

import streamlit as st
from cryptography.fernet import Fernet, InvalidToken

from timewise.config import get_settings

COOKIE_NAME = "timewise_session"
_PENDING_KEY = "_pending_cookie_script"


def _cipher() -> Fernet:
    digest = hashlib.sha256(get_settings().cookie_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def read_token() -> str | None:
    """Return the session token from the request cookie, if present and valid."""
    encrypted = st.context.cookies.get(COOKIE_NAME)
    if not encrypted:
        return None
    try:
        return _cipher().decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def _cookie_script(value: str, max_age_seconds: int | None) -> str:
    attributes = "; path=/; SameSite=Lax"
    if max_age_seconds is not None:
        attributes += f"; max-age={max_age_seconds}"
    cookie = json.dumps(f"{COOKIE_NAME}={value}{attributes}")
    return (
        "<script>document.cookie = "
        f"{cookie} + (location.protocol === 'https:' ? '; Secure' : '');</script>"
    )


def queue_token(token: str, max_age_seconds: int | None) -> None:
    """Store the token in the browser. ``None`` makes a browser-session cookie."""
    encrypted = _cipher().encrypt(token.encode("utf-8")).decode("utf-8")
    st.session_state[_PENDING_KEY] = _cookie_script(encrypted, max_age_seconds)


def queue_removal() -> None:
    st.session_state[_PENDING_KEY] = _cookie_script("", 0)


def flush() -> None:
    """Emit the queued cookie write, if any. Call once near the top of each run."""
    script = st.session_state.pop(_PENDING_KEY, None)
    if script:
        st.html(script, unsafe_allow_javascript=True)
