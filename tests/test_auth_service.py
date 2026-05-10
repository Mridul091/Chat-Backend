import pytest
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings


# ── hash_password / verify_password ─────────────────────────────────────────

def test_hash_password_returns_nonempty_string():
    hashed = hash_password("mysecretpassword")
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_hash_password_is_not_plaintext():
    plain = "mysecretpassword"
    hashed = hash_password(plain)
    assert hashed != plain


def test_verify_password_correct():
    plain = "mysecretpassword"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correctpassword")
    assert verify_password("wrongpassword", hashed) is False


def test_hash_password_different_salts():
    """Two hashes of the same password should not be equal (bcrypt uses random salt)."""
    hashed1 = hash_password("samepassword")
    hashed2 = hash_password("samepassword")
    assert hashed1 != hashed2


# ── create_access_token / decode_access_token ────────────────────────────────

def test_create_access_token_returns_string():
    token = create_access_token(42)
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token_returns_user_id():
    user_id = 7
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id


def test_decode_access_token_invalid_token_returns_none():
    assert decode_access_token("not.a.valid.token") is None


def test_decode_access_token_empty_string_returns_none():
    assert decode_access_token("") is None


def test_decode_access_token_rejects_refresh_token():
    """A refresh token must not be accepted by decode_access_token."""
    refresh = create_refresh_token(5)
    assert decode_access_token(refresh) is None


def test_decode_access_token_expired_returns_none():
    expire = datetime.now(timezone.utc) - timedelta(seconds=1)
    payload = {"sub": "99", "exp": expire}
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_access_token(expired_token) is None


def test_decode_access_token_missing_sub_returns_none():
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {"exp": expire}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_access_token(token) is None


# ── create_refresh_token / decode_refresh_token ──────────────────────────────

def test_create_refresh_token_returns_string():
    token = create_refresh_token(10)
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_refresh_token_returns_user_id():
    user_id = 10
    token = create_refresh_token(user_id)
    assert decode_refresh_token(token) == user_id


def test_decode_refresh_token_invalid_token_returns_none():
    assert decode_refresh_token("not.valid") is None


def test_decode_refresh_token_rejects_access_token():
    """An access token must not be accepted by decode_refresh_token."""
    access = create_access_token(3)
    assert decode_refresh_token(access) is None


def test_decode_refresh_token_expired_returns_none():
    expire = datetime.now(timezone.utc) - timedelta(seconds=1)
    payload = {"sub": "99", "exp": expire, "type": "refresh"}
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_refresh_token(expired_token) is None
