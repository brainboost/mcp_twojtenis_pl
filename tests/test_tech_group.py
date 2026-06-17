import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.tech_group import TechGroupResolver


@pytest.mark.asyncio
async def test_resolves_and_caches(monkeypatch):
    calls: list[str] = []

    async def fake_get(self, url, *, access_token, params=None):
        calls.append(url)
        return {"id": "TechGrp1", "serviceUrl": "https://tech.example", "name": "TG1"}

    monkeypatch.setattr(ApiClient, "get", fake_get)
    c = ApiClient(main_base="https://main.example")
    r = TechGroupResolver(c)
    url1 = await r.service_url_for_club("club-uuid")
    url2 = await r.service_url_for_club("club-uuid")
    assert url1 == url2 == "https://tech.example"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_invalidate_clears_cache(monkeypatch):
    calls: list[str] = []

    async def fake_get(self, url, *, access_token, params=None):
        calls.append(url)
        return {"id": "TechGrp1", "serviceUrl": "https://tech.example", "name": "TG1"}

    monkeypatch.setattr(ApiClient, "get", fake_get)
    r = TechGroupResolver(ApiClient(main_base="https://main.example"))
    await r.service_url_for_club("c")
    r.invalidate("c")
    await r.service_url_for_club("c")
    assert len(calls) == 2
