import time

import jwt
import pytest

from twojtenis_mcp.jwt_utils import decode_sub, is_expired


def _make(sub: str, exp: int) -> str:
    return jwt.encode({"sub": sub, "exp": exp}, "secret", algorithm="HS256")


def test_decode_sub_returns_auth0_subject():
    token = _make("auth0|abc123", int(time.time()) + 3600)
    assert decode_sub(token) == "auth0|abc123"


def test_is_expired_true_when_past_exp():
    token = _make("auth0|x", int(time.time()) - 10)
    assert is_expired(token) is True


def test_is_expired_false_when_future_exp():
    token = _make("auth0|x", int(time.time()) + 3600)
    assert is_expired(token) is False


def test_decode_sub_raises_on_garbage():
    with pytest.raises(ValueError):
        decode_sub("not-a-jwt")
