"""TimeWise entry point. Run with: streamlit run app.py"""

import streamlit as st

from timewise.config import ConfigurationError
from timewise.database import get_database
from timewise.ui import session, session_cookie
from timewise.ui.navigation import run_signed_in_app
from timewise.ui.pages.auth import render_auth_page


def main() -> None:
    session.initialize()
    try:
        get_database()
    except ConfigurationError as error:
        st.error(f"TimeWise is not configured correctly: {error}")
        st.stop()

    session.restore_from_cookie()
    signed_in = session.is_signed_in()
    st.set_page_config(
        page_title="TimeWise",
        page_icon=":material/hourglass_top:",
        layout="wide" if signed_in else "centered",
    )
    session_cookie.flush()

    if signed_in:
        run_signed_in_app()
    else:
        render_auth_page()


main()
