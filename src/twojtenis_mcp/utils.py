from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import quote

_DDMMYYYY = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def to_iso_date(s: str) -> str:
    """Normalize date string to ISO YYYY-MM-DD. Accepts DD.MM.YYYY or already-ISO."""
    if _ISO.match(s):
        datetime.strptime(s, "%Y-%m-%d")
        return s
    if _DDMMYYYY.match(s):
        return datetime.strptime(s, "%d.%m.%Y").strftime("%Y-%m-%d")
    raise ValueError(f"unrecognized date {s!r}; want DD.MM.YYYY or YYYY-MM-DD")


def from_iso_date(s: str) -> str:
    """Convert ISO YYYY-MM-DD to DD.MM.YYYY for human-friendly display."""
    return datetime.strptime(s, "%Y-%m-%d").strftime("%d.%m.%Y")


def encode_auth0_sub(sub: str) -> str:
    """URL-encode an Auth0 subject id (e.g. 'auth0|abc' -> 'auth0%7Cabc')."""
    return quote(sub, safe="")
