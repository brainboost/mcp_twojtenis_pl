import httpx
import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.models import ApiErrorException


@pytest.mark.asyncio
async def test_get_attaches_bearer(monkeypatch):
    captured: dict = {}

    async def fake_send(self, req, **kw):
        captured["url"] = str(req.url)
        captured["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json={"ok": True}, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    c = ApiClient(main_base="https://main.example", timeout=5)
    out = await c.get("https://main.example/api/v1/Players/me", access_token="tok123")
    assert out == {"ok": True}
    assert captured["auth"] == "Bearer tok123"
    assert captured["url"] == "https://main.example/api/v1/Players/me"


@pytest.mark.asyncio
async def test_get_public_omits_auth(monkeypatch):
    captured: dict = {}

    async def fake_send(self, req, **kw):
        captured["auth"] = req.headers.get("authorization")
        return httpx.Response(200, json=[], request=req)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    c = ApiClient(main_base="https://main.example", timeout=5)
    await c.get(
        "https://main.example/api/v1/clubs/x/excludes/public?date=2026-05-11",
        access_token=None,
    )
    assert captured["auth"] is None


@pytest.mark.asyncio
async def test_post_json_passes_body(monkeypatch):
    captured: dict = {}

    async def fake_send(self, req, **kw):
        captured["body"] = req.content
        captured["ct"] = req.headers.get("content-type")
        return httpx.Response(200, json={"ok": 1}, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    c = ApiClient(main_base="https://main.example", timeout=5)
    await c.post("https://main.example/x", access_token="t", json={"a": 1})
    assert b'"a": 1' in captured["body"] or b'"a":1' in captured["body"]
    assert captured["ct"].startswith("application/json")


@pytest.mark.asyncio
async def test_401_maps_to_authentication_required(monkeypatch):
    async def fake_send(self, req, **kw):
        return httpx.Response(401, json={"message": "expired"}, request=req)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    c = ApiClient(main_base="https://main.example", timeout=5)
    with pytest.raises(ApiErrorException) as ei:
        await c.get("https://main.example/x", access_token="t")
    assert ei.value.code == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_5xx_maps_to_http_error(monkeypatch):
    async def fake_send(self, req, **kw):
        return httpx.Response(503, text="boom", request=req)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    c = ApiClient(main_base="https://main.example", timeout=5)
    with pytest.raises(ApiErrorException) as ei:
        await c.get("https://main.example/x", access_token="t")
    assert ei.value.code == "HTTP_ERROR"
