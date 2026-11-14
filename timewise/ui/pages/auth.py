"""Sign-in, sign-up and password recovery screens."""

import streamlit as st

from timewise.auth import accounts
from timewise.errors import ValidationError
from timewise.ui import session

_FEATURES = (
    ("⏱️", "Log your day", "Capture what you did in seconds."),
    ("📊", "See where time goes", "Clear breakdowns by category and by week."),
    ("✨", "Get advice that fits", "AI suggestions grounded in your own data."),
)


def _show(view: str) -> None:
    st.session_state.auth_view = view
    st.rerun()


def _render_brand_panel() -> None:
    with st.container(key="auth-hero"):
        st.title("TimeWise")
        st.markdown("### Spend your time on purpose.")
        for emoji, heading, detail in _FEATURES:
            st.markdown(f"{emoji} **{heading}**  \n{detail}")


def _render_login() -> None:
    st.subheader("Welcome back 👋")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        remember = st.checkbox("Keep me signed in for 30 days")
        submitted = st.form_submit_button("Sign in", type="primary", width="stretch")

    if submitted:
        user = accounts.authenticate(username, password)
        if user is None:
            st.error("Incorrect username or password.")
        else:
            session.sign_in(user, remember)
            st.rerun()

    signup, recovery = st.columns(2)
    if signup.button("Create an account", width="stretch"):
        _show("signup")
    if recovery.button("Forgot password?", type="tertiary", width="stretch"):
        _show("recovery")


def _render_signup() -> None:
    st.subheader("Create your account 🚀")
    with st.form("signup_form"):
        name = st.text_input("Name")
        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password",
            help=f"At least {accounts.MIN_PASSWORD_LENGTH} characters.",
        )
        confirmation = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create account", type="primary", width="stretch")

    if submitted:
        if password != confirmation:
            st.error("Passwords do not match.")
        else:
            try:
                user, recovery_code = accounts.register(name, username, password)
            except ValidationError as error:
                st.error(str(error))
            else:
                session.sign_in(user, remember=False)
                st.session_state.recovery_code = recovery_code
                st.rerun()

    if st.button("Back to sign in", type="tertiary", width="stretch"):
        _show("login")


def _render_recovery() -> None:
    st.subheader("Reset your password 🔑")
    st.caption("Use the recovery code you saved when you signed up.")
    with st.form("recovery_form"):
        username = st.text_input("Username")
        recovery_code = st.text_input("Recovery code", placeholder="XXXX-XXXX-XXXX")
        password = st.text_input("New password", type="password")
        confirmation = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Reset password", type="primary", width="stretch")

    if submitted:
        if password != confirmation:
            st.error("Passwords do not match.")
        else:
            try:
                user, new_code = accounts.reset_password(username, recovery_code, password)
            except ValidationError as error:
                st.error(str(error))
            else:
                session.sign_in(user, remember=False)
                st.session_state.recovery_code = new_code
                session.flash("Password updated.")
                st.rerun()

    if st.button("Back to sign in", type="tertiary", width="stretch"):
        _show("login")


_VIEWS = {
    "login": _render_login,
    "signup": _render_signup,
    "recovery": _render_recovery,
}


def render_auth_page() -> None:
    _, brand, form, _ = st.columns([0.4, 4, 3.6, 0.4], gap="large", vertical_alignment="center")
    with brand:
        _render_brand_panel()
    with form:
        _VIEWS[st.session_state.auth_view]()
