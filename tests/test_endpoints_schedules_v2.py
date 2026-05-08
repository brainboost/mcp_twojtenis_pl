import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.endpoints.schedules import SchedulesEndpoint
from twojtenis_mcp.models import ApiErrorException
from twojtenis_mcp.tech_group import TechGroupResolver


@pytest.mark.asyncio
async def test_get_schedule_combines_public_and_excludes(monkeypatch):
    seen: list[tuple[str, dict | None]] = []

    async def fake_get(self, url, *, access_token, params=None):
        seen.append((url, dict(params) if params else None))
        if "/technical-group" in url:
            return {"id": "TG", "serviceUrl": "https://tech.example", "name": "TG"}
        if "/bookings/public" in url:
            return [
                {
                    "clubId": "c",
                    "date": "2026-05-11",
                    "startTime": "15:00:00",
                    "endTime": "17:00:00",
                    "locationId": "loc1",
                    "id": "b1",
                    "price": None,
                }
            ]
        if "/excludes/public" in url:
            return []
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main.example")
    ep = SchedulesEndpoint(client, TechGroupResolver(client))
    out = await ep.get_club_schedule(club_id="c", date="11.05.2026", access_token="t")
    assert out["success"] is True
    assert out["data"]["date"] == "2026-05-11"
    assert out["data"]["bookings"][0]["start_time"] == "15:00:00"
    assert out["data"]["bookings"][0]["location_id"] == "loc1"
    assert out["data"]["excludes"] == []


@pytest.mark.asyncio
async def test_invalid_date_raises():
    client = ApiClient(main_base="https://main.example")
    ep = SchedulesEndpoint(client, TechGroupResolver(client))
    with pytest.raises(ApiErrorException) as ei:
        await ep.get_club_schedule(club_id="c", date="not-a-date", access_token="t")
    assert ei.value.code == "VALIDATION_ERROR"
