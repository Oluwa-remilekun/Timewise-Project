"""Page registry and layout for the signed-in application."""

import streamlit as st

from timewise.ui import session
from timewise.ui.components.user_menu import render_user_menu
from timewise.ui.pages.analyser import render_analyser_page
from timewise.ui.pages.calendar import render_calendar_page
from timewise.ui.pages.home import render_home_page
from timewise.ui.pages.reminders import render_reminders_page
from timewise.ui.pages.todo import render_todo_page


@st.dialog("Save your recovery code", dismissible=False)
def _recovery_code_dialog(code: str) -> None:
    st.write(
        "This code is the only way to reset your password if you forget it. "
        "Store it somewhere safe; it will not be shown again."
    )
    st.code(code, language=None)
    if st.button("I have saved it", type="primary", width="stretch"):
        st.session_state.recovery_code = None
        st.rerun()


def _build_pages() -> dict:
    return {
        "home": st.Page(render_home_page, title="Home", icon=":material/home:", default=True),
        "analyser": st.Page(
            render_analyser_page,
            title="Time Analyser",
            icon=":material/monitoring:",
            url_path="analyser",
        ),
        "todo": st.Page(
            render_todo_page, title="To-do", icon=":material/checklist:", url_path="todo"
        ),
        "calendar": st.Page(
            render_calendar_page,
            title="Calendar",
            icon=":material/calendar_month:",
            url_path="calendar",
        ),
        "reminders": st.Page(
            render_reminders_page,
            title="Reminders",
            icon=":material/notifications:",
            url_path="reminders",
        ),
    }


def run_signed_in_app() -> None:
    pages = _build_pages()
    session.set_pages(pages)
    current_page = st.navigation(list(pages.values()), position="top")

    render_user_menu()
    session.show_flash()
    if st.session_state.recovery_code:
        _recovery_code_dialog(st.session_state.recovery_code)
    current_page.run()
