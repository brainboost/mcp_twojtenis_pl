from __future__ import annotations

import time

import jwt


def decode_sub(token: str) -> str:
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise ValueError(f"invalid jwt: {exc}") from exc
    sub = claims.get("sub")
    if not sub:
        raise ValueError("jwt has no sub claim")
    return sub


def is_expired(token: str, leeway_s: int = 30) -> bool:
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return True
    exp = claims.get("exp")
    if exp is None:
        return False
    return int(time.time()) + leeway_s >= int(exp)
