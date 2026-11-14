"""Account menu shown at the top of every signed-in page."""

import streamlit as st

from timewise.ui import session


def render_user_menu() -> None:
    user = session.current_user()
    _, menu = st.columns([4, 1])
    with menu.popover(user.name, icon=":material/account_circle:", width="stretch"):
        st.caption(f"Signed in as @{user.username}")
        if st.button("Sign out", icon=":material/logout:", width="stretch"):
            session.sign_out()
            st.rerun()
