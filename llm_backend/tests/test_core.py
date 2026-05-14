"""测试核心模块：配置、安全、密码"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.hashing import get_password_hash, verify_password
from app.core.security import create_access_token


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None


class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = get_password_hash("test123456")
        assert isinstance(h, str)
        assert h.startswith("$2b$")

    def test_verify_correct(self):
        h = get_password_hash("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong(self):
        h = get_password_hash("mypassword")
        assert verify_password("wrong", h) is False

    def test_verify_empty(self):
        h = get_password_hash("")
        assert verify_password("", h) is True

    def test_different_salts(self):
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2
        assert verify_password("same", h1)
        assert verify_password("same", h2)


class TestJWTToken:
    def test_roundtrip(self):
        token = create_access_token({"sub": "42"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_roundtrip_various_ids(self):
        for uid in ["1", "100", "9999"]:
            token = create_access_token({"sub": uid})
            payload = decode_token(token)
            assert payload is not None
            assert payload["sub"] == uid

    def test_roundtrip_with_extra_data(self):
        token = create_access_token({"sub": "user@test.com", "role": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user@test.com"
        assert payload.get("role") == "admin"

    def test_decode_invalid(self):
        assert decode_token("not.a.valid.token") is None
        assert decode_token("") is None
        assert decode_token(None) is None

    def test_decode_garbage(self):
        assert decode_token("abcdefghijklmnop") is None

    def test_token_contains_exp(self):
        token = create_access_token({"sub": "1"})
        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload

    def test_custom_expiry(self):
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(hours=1))
        payload = decode_token(token)
        assert payload is not None
