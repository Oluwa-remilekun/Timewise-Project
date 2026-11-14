"""Signed-in user summary and sign-out button in the sidebar."""

import streamlit as st

from timewise.ui import session


def render_user_menu() -> None:
    user = session.current_user()
    with st.sidebar.container(key="user-card"):
        st.markdown(f":material/account_circle: **{user.name}**")
        st.caption(f"@{user.username}")
        if st.button("Sign out", icon=":material/logout:", width="stretch"):
            session.sign_out()
            st.rerun()
