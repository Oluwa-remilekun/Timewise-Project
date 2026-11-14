from datetime import timedelta

import pytest

from timewise.auth import accounts, passwords, sessions
from timewise.database import get_database
from timewise.errors import ValidationError


def test_hash_secret_is_salted_and_verifiable():
    first = passwords.hash_secret("correct-horse")
    second = passwords.hash_secret("correct-horse")
    assert first != second
    assert "correct-horse" not in first
    assert passwords.verify_secret("correct-horse", first)
    assert not passwords.verify_secret("wrong-horse", first)


@pytest.mark.parametrize("stored", ["", "not-a-hash", "md5$1$zz$abc", "a$b$c$d"])
def test_verify_secret_rejects_malformed_hashes(stored):
    assert passwords.verify_secret("anything", stored) is False


def test_register_normalizes_username_and_stores_no_plaintext():
    user, recovery_code = accounts.register("  Remi  ", "  Remi_A  ", "correct-horse")
    assert (user.name, user.username) == ("Remi", "remi_a")

    db = get_database()
    row = db.query(f"SELECT * FROM {db.table('users')}")[0]
    assert "correct-horse" not in row.values()
    assert recovery_code not in row.values()


@pytest.mark.parametrize(
    ("name", "username", "password"),
    [
        ("", "remi", "correct-horse"),
        ("Remi", "ab", "correct-horse"),
        ("Remi", "has space", "correct-horse"),
        ("Remi", "remi", "short"),
    ],
)
def test_register_rejects_invalid_input(name, username, password):
    with pytest.raises(ValidationError):
        accounts.register(name, username, password)


def test_register_rejects_duplicate_username(user):
    with pytest.raises(ValidationError, match="already taken"):
        accounts.register("Other", "REMI", "another-password")


def test_authenticate(user):
    assert accounts.authenticate("Remi ", "correct-horse") == user
    assert accounts.authenticate("remi", "wrong-password") is None
    assert accounts.authenticate("nobody", "correct-horse") is None
    assert accounts.authenticate("", "") is None


def test_recovery_code_format():
    code = accounts.generate_recovery_code()
    assert len(code) == 14
    assert code.count("-") == 2
    assert accounts.normalize_recovery_code(code.lower().replace("-", " ")) == code.replace("-", "")


def test_reset_password_with_recovery_code_rotates_the_code():
    user, recovery_code = accounts.register("Remi", "remi", "correct-horse")

    same_user, new_code = accounts.reset_password("remi", recovery_code.lower(), "brand-new-pass")

    assert same_user == user
    assert new_code != recovery_code
    assert accounts.authenticate("remi", "brand-new-pass") == user
    assert accounts.authenticate("remi", "correct-horse") is None
    with pytest.raises(ValidationError):
        accounts.reset_password("remi", recovery_code, "another-new-pass")


def test_reset_password_does_not_create_a_duplicate_account():
    _, recovery_code = accounts.register("Remi", "remi", "correct-horse")
    accounts.reset_password("remi", recovery_code, "brand-new-pass")
    db = get_database()
    assert len(db.query(f"SELECT id FROM {db.table('users')}")) == 1


@pytest.mark.parametrize(
    ("username", "code"), [("remi", "0000-0000-0000"), ("nobody", "0000-0000-0000")]
)
def test_reset_password_rejects_wrong_code_or_user(user, username, code):
    with pytest.raises(ValidationError, match="incorrect"):
        accounts.reset_password(username, code, "brand-new-pass")
    assert accounts.authenticate("remi", "correct-horse") == user


def test_reset_password_enforces_password_length():
    _, recovery_code = accounts.register("Remi", "remi", "correct-horse")
    with pytest.raises(ValidationError, match="at least"):
        accounts.reset_password("remi", recovery_code, "short")


def test_session_round_trip_stores_only_a_hash(user):
    token, _ = sessions.start_session(user.id, remember=True)

    assert sessions.resolve_session(token) == user
    db = get_database()
    stored = db.query(f"SELECT token_hash FROM {db.table('sessions')}")[0]["token_hash"]
    assert stored != token


def test_session_lifetime_depends_on_remember_me(user):
    _, short_expiry = sessions.start_session(user.id, remember=False)
    _, long_expiry = sessions.start_session(user.id, remember=True)
    assert long_expiry - short_expiry >= timedelta(days=28)


def test_unknown_or_empty_tokens_resolve_to_nobody(user):
    sessions.start_session(user.id, remember=True)
    assert sessions.resolve_session("forged-token") is None
    assert sessions.resolve_session("") is None
    assert sessions.resolve_session(None) is None


def test_end_session_invalidates_only_that_token(user):
    first, _ = sessions.start_session(user.id, remember=True)
    second, _ = sessions.start_session(user.id, remember=True)

    sessions.end_session(first)

    assert sessions.resolve_session(first) is None
    assert sessions.resolve_session(second) == user


def test_expired_sessions_are_rejected_and_purged(user, monkeypatch):
    token, expires_at = sessions.start_session(user.id, remember=False)
    monkeypatch.setattr(sessions, "utc_now", lambda: expires_at + timedelta(seconds=1))

    assert sessions.resolve_session(token) is None

    sessions.start_session(user.id, remember=False)
    db = get_database()
    assert len(db.query(f"SELECT id FROM {db.table('sessions')}")) == 1


def test_password_reset_signs_out_existing_sessions():
    user, recovery_code = accounts.register("Remi", "remi", "correct-horse")
    token, _ = sessions.start_session(user.id, remember=True)

    accounts.reset_password("remi", recovery_code, "brand-new-pass")

    assert sessions.resolve_session(token) is None
