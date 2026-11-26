from datetime import date, datetime
from types import SimpleNamespace

import pytest

from timewise.ai import advisor, client, event_parser, prompts
from timewise.ai.client import AIUnavailableError
from timewise.config import get_settings
from timewise.models import Activity, Task

TODAY = date(2026, 11, 14)
NOW = datetime(2026, 11, 14, 9, 0)
SUMMARY = {"Productive": 60, "Unproductive": 120, "Fun": 0}
ACTIVITIES = [
    Activity("1", "Scrolling TikTok", "Unproductive", 120, TODAY),
    Activity("2", "Calculus homework", "Productive", 60, TODAY),
]
TASKS = [
    Task("1", "Lab report", "", "School", TODAY, False),
    Task("2", "Pay rent", "before 5pm", "Urgent", TODAY, False),
    Task("3", "Laundry", "", "Life", TODAY, True),
]


@pytest.fixture
def gemini(monkeypatch):
    """Replace the Gemini SDK client with a recorder that returns a canned reply."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    calls = []
    fake = SimpleNamespace(reply="- Do less scrolling.", error=None, calls=calls)

    def generate_content(**kwargs):
        calls.append(kwargs)
        if fake.error:
            raise fake.error
        return SimpleNamespace(text=fake.reply)

    sdk_client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(client, "_get_client", lambda: sdk_client)
    return fake


def test_generate_text_requires_an_api_key():
    assert client.is_configured() is False
    with pytest.raises(AIUnavailableError, match="GEMINI_API_KEY"):
        client.generate_text("hello", system_instruction="be brief")


def test_generate_text_sends_model_prompt_and_config(gemini):
    reply = client.generate_text("hello", system_instruction="be brief", temperature=0.2)

    assert reply == "- Do less scrolling."
    call = gemini.calls[0]
    assert call["model"] == "gemini-flash-latest"
    assert call["contents"] == "hello"
    assert call["config"].system_instruction == "be brief"
    assert call["config"].temperature == 0.2
    assert call["config"].response_mime_type == "text/plain"


def test_generate_text_wraps_sdk_failures(gemini):
    gemini.error = ConnectionError("quota exceeded")
    with pytest.raises(AIUnavailableError, match="quota exceeded"):
        client.generate_text("hello", system_instruction="be brief")


@pytest.mark.parametrize("reply", ["", "   ", None])
def test_generate_text_rejects_empty_replies(gemini, reply):
    gemini.reply = reply
    with pytest.raises(AIUnavailableError, match="empty"):
        client.generate_text("hello", system_instruction="be brief")


def test_activity_prompt_is_grounded_in_the_users_data():
    prompt = prompts.activity_advice_prompt(SUMMARY, ACTIVITIES, TODAY)
    assert "Saturday, November 14, 2026" in prompt
    assert "- Unproductive: 2h (67%)" in prompt
    assert "- Scrolling TikTok: 2h (Unproductive)" in prompt
    assert "- Calculus homework: 1h (Productive)" in prompt


def test_task_prompts_list_task_details():
    overview = prompts.daily_overview_prompt(TASKS, TODAY)
    assert "Completed: Laundry" in overview
    assert "Lab report (School), Pay rent (Urgent)" in overview

    priorities = prompts.task_priorities_prompt(TASKS[:2], TODAY)
    assert "- Pay rent (category: Urgent, due: 2026-11-14, notes: before 5pm)" in priorities


def test_activity_advice_uses_gemini_when_available(gemini):
    advice = advisor.activity_advice(SUMMARY, ACTIVITIES, TODAY)

    assert advice == advisor.Advice("- Do less scrolling.", is_ai_generated=True)
    assert "Scrolling TikTok" in gemini.calls[0]["contents"]
    assert gemini.calls[0]["config"].system_instruction == prompts.COACH_INSTRUCTION


def test_activity_advice_falls_back_to_rules_without_a_key():
    advice = advisor.activity_advice(SUMMARY, ACTIVITIES, TODAY)

    assert advice.is_ai_generated is False
    assert "Scrolling TikTok" in advice.text
    assert "No fun time logged" in advice.text


def test_activity_advice_falls_back_when_the_request_fails(gemini):
    gemini.error = TimeoutError("timed out")
    advice = advisor.activity_advice(
        {"Productive": 90, "Unproductive": 0, "Fun": 90}, ACTIVITIES[1:], TODAY
    )
    assert advice.is_ai_generated is False
    assert "50% of your tracked time was productive" in advice.text
    assert "Fun took over 40%" in advice.text


def test_daily_overview_fallbacks_cover_every_task_state():
    assert "Nothing is due today" in advisor.daily_overview([], TODAY).text
    assert "Everything due today is done" in advisor.daily_overview(TASKS[2:], TODAY).text

    with_pending = advisor.daily_overview(TASKS, TODAY).text
    assert 'Start with "Pay rent"' in with_pending
    assert "2 of 3 tasks remain" in with_pending


def test_task_priorities_fallback_puts_urgent_first():
    advice = advisor.task_priorities(TASKS[:2], TODAY)
    assert advice.is_ai_generated is False
    assert advice.text.index("Pay rent") < advice.text.index("Lab report")


def test_parse_event_reads_the_json_reply(gemini):
    gemini.reply = (
        '{"title": " Study group ", "start": "2026-11-15T14:00", "end": "2026-11-15T15:30"}'
    )

    draft = event_parser.parse_event("Study group tomorrow at 2 PM for 90 minutes", NOW)

    assert draft == event_parser.EventDraft(
        "Study group", datetime(2026, 11, 15, 14, 0), datetime(2026, 11, 15, 15, 30)
    )
    call = gemini.calls[0]
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].temperature == 0
    assert "Saturday 2026-11-14T09:00" in call["contents"]


def test_parse_event_drops_time_zone_offsets(gemini):
    gemini.reply = (
        '{"title": "Call", "start": "2026-11-15T14:00:00-06:00", '
        '"end": "2026-11-15T15:00:00-06:00"}'
    )
    draft = event_parser.parse_event("Call tomorrow at 2", NOW)
    assert draft.starts_at == datetime(2026, 11, 15, 14, 0)


@pytest.mark.parametrize(
    "reply",
    [
        "not json",
        "[]",
        '{"title": "Call"}',
        '{"title": "Call", "start": "tomorrow", "end": "later"}',
        '{"title": "", "start": "2026-11-15T14:00", "end": "2026-11-15T15:00"}',
        '{"title": "Call", "start": "2026-11-15T15:00", "end": "2026-11-15T14:00"}',
    ],
)
def test_parse_event_rejects_unusable_replies(gemini, reply):
    gemini.reply = reply
    with pytest.raises(AIUnavailableError, match="not a valid event"):
        event_parser.parse_event("Call tomorrow", NOW)


@pytest.mark.parametrize(
    "reply",
    [
        '```json\n{"title": "Honors thesis meeting", "start": "2026-11-27T14:00", '
        '"end": "2026-11-27T15:00"}\n```',
        '[{"title": "Honors thesis meeting", "start": "2026-11-27T14:00", '
        '"end": "2026-11-27T15:00"}]',
        '{"title": "Honors thesis meeting", "start": "2026-11-27T14:00:00Z", '
        '"end": "2026-11-27T15:00:00Z"}',
        '{"title": "Honors thesis meeting", "start": "2026-11-27T14:00"}',
        '{"title": "Honors thesis meeting", "start": "2026-11-27T14:00", "end": null}',
    ],
)
def test_parse_event_tolerates_common_reply_shapes(gemini, reply):
    gemini.reply = reply

    draft = event_parser.parse_event(
        "meeting with tempest henning for honors thesis discussion on friday nov 27 at 2pm",
        datetime(2026, 11, 26, 10, 0),
    )

    assert draft == event_parser.EventDraft(
        "Honors thesis meeting", datetime(2026, 11, 27, 14, 0), datetime(2026, 11, 27, 15, 0)
    )


def test_unusable_event_reply_gives_a_user_facing_reason(gemini):
    gemini.reply = "Sure! Your meeting is on Friday."
    with pytest.raises(AIUnavailableError) as raised:
        event_parser.parse_event("meeting friday", NOW)
    assert "not with a usable event" in raised.value.reason


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("400 INVALID_ARGUMENT. API key not valid. Please pass a valid API key.", "API key"),
        ("403 PERMISSION_DENIED.", "API key"),
        ("404 NOT_FOUND. models/gemini-x is not found for API version v1beta", "not available"),
        ("429 RESOURCE_EXHAUSTED. Quota exceeded.", "free-tier limit"),
        ("Connection reset by peer", "could not be reached"),
    ],
)
def test_sdk_errors_are_explained_to_the_user(gemini, message, expected):
    gemini.error = RuntimeError(message)
    with pytest.raises(AIUnavailableError) as raised:
        client.generate_text("hello", system_instruction="be brief")
    assert expected in raised.value.reason


def test_missing_key_reason_and_fallback_note():
    advice = advisor.activity_advice(SUMMARY, ACTIVITIES, TODAY)
    assert advice.note == "Set GEMINI_API_KEY to enable AI features."
