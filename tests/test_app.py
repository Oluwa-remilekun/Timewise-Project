"""UI tests that drive the Streamlit app through its testing harness."""

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from timewise.auth import accounts
from timewise.repositories import activities, events, reminders, tasks
from timewise.ui import session_cookie

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
TIMEOUT_SECONDS = 30


@pytest.fixture(autouse=True)
def no_browser_cookie(monkeypatch):
    monkeypatch.setattr(session_cookie, "read_token", lambda: None)


def button(app: AppTest, label: str):
    return next(element for element in app.button if element.label == label)


def launch() -> AppTest:
    app = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT_SECONDS).run()
    assert not app.exception
    return app


def sign_up(app: AppTest, password: str = "correct-horse") -> AppTest:
    button(app, "Create an account").click().run()
    for field, value in zip(
        app.text_input, ["Remi Adeshina", "remi", password, password], strict=True
    ):
        field.set_value(value)
    return button(app, "Create account").click().run()


def test_signed_out_visitors_see_the_login_form():
    app = launch()
    assert app.title[0].value == "TimeWise"
    assert [field.label for field in app.text_input] == ["Username", "Password"]


def test_login_with_wrong_credentials_shows_a_generic_error():
    app = launch()
    app.text_input[0].set_value("nobody")
    app.text_input[1].set_value("wrong-password")
    button(app, "Sign in").click().run()
    assert [error.value for error in app.error] == ["Incorrect username or password."]


def test_sign_up_signs_in_and_shows_the_recovery_code_once():
    app = sign_up(launch())

    assert not app.exception
    assert app.title[0].value.endswith(", Remi")
    recovery_code = app.code[0].value
    assert len(recovery_code) == 14

    button(app, "I have saved it").click().run()
    assert not app.code
    assert app.title[0].value.endswith(", Remi")


def test_sign_up_reports_validation_errors():
    app = sign_up(launch(), password="short")
    assert "at least 8 characters" in app.error[0].value
    assert app.title[0].value == "TimeWise"


def test_login_then_sign_out_returns_to_the_login_form(user):
    app = launch()
    app.text_input[0].set_value("remi")
    app.text_input[1].set_value("correct-horse")
    button(app, "Sign in").click().run()
    assert app.title[0].value.endswith(", Remi")

    button(app, "Sign out").click().run()
    assert app.title[0].value == "TimeWise"
    assert app.session_state.user is None


def test_password_recovery_signs_in_and_issues_a_new_code():
    _, recovery_code = accounts.register("Remi Adeshina", "remi", "correct-horse")
    app = launch()
    button(app, "Forgot password?").click().run()
    for field, value in zip(
        app.text_input, ["remi", recovery_code, "brand-new-pass", "brand-new-pass"], strict=True
    ):
        field.set_value(value)
    button(app, "Reset password").click().run()

    assert not app.exception
    assert app.title[0].value.endswith(", Remi")
    assert app.code[0].value != recovery_code
    assert accounts.authenticate("remi", "brand-new-pass") is not None


def render_page(page_name: str, user_id: str, name: str, username: str) -> None:
    """Script body for AppTest: sign a user in and render a single page."""
    import streamlit as st

    from timewise.models import User
    from timewise.ui import navigation, session

    session.initialize()
    st.session_state.user = User(user_id, name, username)
    pages = navigation._build_pages()
    session.set_pages(pages)
    st.navigation(list(pages.values()), position="hidden")
    getattr(navigation, f"render_{page_name}_page")()


def open_page(page_name: str, user) -> AppTest:
    app = AppTest.from_function(
        render_page,
        args=(page_name, user.id, user.name, user.username),
        default_timeout=TIMEOUT_SECONDS,
    ).run()
    assert not app.exception
    return app


@pytest.mark.parametrize("page_name", ["home", "analyser", "todo", "calendar", "reminders"])
def test_every_page_renders_for_a_new_user(user, page_name):
    open_page(page_name, user)


@pytest.fixture
def populated_user(user):
    today = date.today()
    now = datetime.now().replace(second=0, microsecond=0)
    activities.add_activity(user.id, "Calculus homework", "Productive", 90, today)
    activities.add_activity(user.id, "Scrolling", "Unproductive", 30, today)
    tasks.add_task(user.id, "Lab report", "School", today, "two pages")
    tasks.add_task(user.id, "Old chore", "Life", today - timedelta(days=3))
    events.add_event(user.id, "Study group", now + timedelta(hours=2), now + timedelta(hours=3))
    reminders.add_reminder(user.id, "Lab report", "Task", now - timedelta(hours=1))
    reminders.add_reminder(user.id, "Study group", "Event", now + timedelta(hours=1), 60)
    return user


@pytest.mark.parametrize("page_name", ["home", "analyser", "todo", "calendar", "reminders"])
def test_every_page_renders_with_data(populated_user, page_name):
    open_page(page_name, populated_user)


def test_home_summarizes_the_day(populated_user):
    app = open_page("home", populated_user)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["⏱️ Tracked today"] == "2h"
    assert metrics["🎯 Productive share"] == "75%"
    assert metrics["✅ Tasks done today"] == "0 of 1"
    assert any("1 day" in block.value for block in app.markdown)
    assert any("Lab report" in warning.value for warning in app.warning)


def test_checking_a_task_on_home_saves_it(populated_user):
    app = open_page("home", populated_user)
    app.checkbox[0].check().run()

    assert not app.exception
    due_today = tasks.list_tasks_due_on(populated_user.id, date.today())
    assert due_today[0].is_completed is True
    assert app.session_state.celebrate is True


def test_dismissing_a_due_reminder_removes_it(populated_user):
    app = open_page("home", populated_user)
    button(app, "Dismiss").click().run()

    assert not app.exception
    remaining = reminders.list_reminders(populated_user.id)
    assert [reminder.title for reminder in remaining] == ["Study group"]


def test_analyser_shows_breakdown_and_rule_based_advice_without_a_key(populated_user):
    app = open_page("analyser", populated_user)
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics == {
        "⏱️ Total tracked": "2h",
        "🎯 Productive": "1h 30m",
        "🌀 Unproductive": "30m",
        "🎉 Fun": "0m",
    }
    assert any("Locked in" in block.value for block in app.markdown)

    button(app, "Get suggestions").click().run()
    assert not app.exception
    assert any("75% of your tracked time was productive" in block.value for block in app.markdown)
    assert any("rule-based tips" in caption.value for caption in app.caption)


def test_todo_add_task_form_creates_a_task(user):
    app = open_page("todo", user)
    app.text_input[0].set_value("Buy textbooks")
    button(app, "Add task").click().run()

    assert not app.exception
    assert [task.title for task in tasks.list_tasks(user.id)] == ["Buy textbooks"]


def test_todo_rejects_an_empty_title(user):
    app = open_page("todo", user)
    button(app, "Add task").click().run()
    assert app.error[0].value == "Task title is required."
    assert tasks.list_tasks(user.id) == []


def test_todo_marks_overdue_tasks(populated_user):
    app = open_page("todo", populated_user)
    assert any("overdue" in caption.value for caption in app.caption)
