import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.endpoints.schedules import SchedulesEndpoint
from twojtenis_mcp.locations import LocationsService
from twojtenis_mcp.models import ApiErrorException
from twojtenis_mcp.router import ApiRouter
from twojtenis_mcp.tech_group import TechGroupResolver

CLUB_DETAILS = {
    "id": "c",
    "name": "Klub",
    "openHours": {
        d: {"from": "09:00:00", "to": "11:00:00"}
        for d in (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
    },
    "locations": [
        {
            "id": "loc-1",
            "name": "Kort 1",
            "type": 0,
            "tags": "Tennis",
            "isEnabled": True,
            "sortNumber": 1,
        },
        {
            "id": "loc-2",
            "name": "Badminton 2",
            "type": 1,
            "tags": "Badminton",
            "isEnabled": True,
            "sortNumber": 2,
        },
    ],
}


@pytest.mark.asyncio
async def test_get_schedule_returns_availability_grid(monkeypatch):
    seen: list[str] = []

    async def fake_get(self, url, *, access_token, params=None):
        seen.append(url)
        if url.endswith("/api/v1/Clubs/c"):
            return CLUB_DETAILS
        if "/technical-group" in url:
            return {"id": "TG", "serviceUrl": "https://tech.example", "name": "TG"}
        if "/bookings/public" in url:
            return [
                {
                    "clubId": "c",
                    "date": "2026-05-11",
                    "startTime": "10:00:00",
                    "endTime": "10:30:00",
                    "locationId": "loc-1",
                    "id": "b1",
                }
            ]
        if "/excludes/public" in url:
            return []
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main.example")
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main.example", resolver=resolver)
    locations = LocationsService(client, router)
    ep = SchedulesEndpoint(client, router, locations)
    out = await ep.get_club_schedule(club_id="c", date="11.05.2026")
    assert out["success"] is True
    assert out["data"]["date"] == "2026-05-11"

    grid = out["data"]["availability"]
    assert {c["location_id"] for c in grid} == {"loc-1", "loc-2"}

    by_loc = {c["location_id"]: c for c in grid}
    loc1_slots = {s["start"]: s["available"] for s in by_loc["loc-1"]["slots"]}
    assert loc1_slots == {
        "09:00": True,
        "09:30": True,
        "10:00": False,  # booked
        "10:30": True,
    }
    # loc-2 has no bookings on this day
    loc2_slots = {s["start"]: s["available"] for s in by_loc["loc-2"]["slots"]}
    assert all(loc2_slots.values())
    assert by_loc["loc-1"]["sport"] == "tennis"
    assert by_loc["loc-2"]["sport"] == "badminton"


@pytest.mark.asyncio
async def test_invalid_date_raises():
    client = ApiClient(main_base="https://main.example")
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main.example", resolver=resolver)
    ep = SchedulesEndpoint(client, router, LocationsService(client, router))
    with pytest.raises(ApiErrorException) as ei:
        await ep.get_club_schedule(club_id="c", date="not-a-date")
    assert ei.value.code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_club_details_cached_across_calls(monkeypatch):
    detail_fetches = 0

    async def fake_get(self, url, *, access_token, params=None):
        nonlocal detail_fetches
        if url.endswith("/api/v1/Clubs/c"):
            detail_fetches += 1
            return CLUB_DETAILS
        if "/technical-group" in url:
            return {"id": "TG", "serviceUrl": "https://tech.example", "name": "TG"}
        if "/bookings/public" in url or "/excludes/public" in url:
            return []
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main.example")
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main.example", resolver=resolver)
    locations = LocationsService(client, router)
    ep = SchedulesEndpoint(client, router, locations)
    await ep.get_club_schedule(club_id="c", date="2026-05-11")
    await ep.get_club_schedule(club_id="c", date="2026-05-12")
    # Same LocationsService instance also serves get_club_locations
    await locations.locations_for_club("c")
    assert detail_fetches == 1
