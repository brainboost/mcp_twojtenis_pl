import pytest

from twojtenis_mcp.utils import encode_auth0_sub, from_iso_date, to_iso_date


def test_to_iso_from_dd_mm_yyyy():
    assert to_iso_date("11.05.2026") == "2026-05-11"


def test_to_iso_passthrough_iso():
    assert to_iso_date("2026-05-11") == "2026-05-11"


def test_to_iso_invalid():
    with pytest.raises(ValueError):
        to_iso_date("garbage")


def test_to_iso_invalid_iso_calendar():
    with pytest.raises(ValueError):
        to_iso_date("2026-13-40")


def test_from_iso():
    assert from_iso_date("2026-05-11") == "11.05.2026"


def test_encode_auth0_sub():
    assert encode_auth0_sub("auth0|abc123") == "auth0%7Cabc123"
