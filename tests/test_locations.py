import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.locations import LocationsService


CLUB_DETAILS_WITH_LOCATIONS = {
    "id": "c",
    "name": "Klub",
    "owner": {},
    "priceLists": [],
    "exceptions": [],
    "locations": [
        {
            "id": "loc-2",
            "name": "Badminton 2",
            "shortName": "B2",
            "hasLight": True,
            "isEnabled": True,
            "tags": "Badminton;Indoor",
            "sortNumber": 12,
            "type": 1,
            "groupName": None,
        },
        {
            "id": "loc-1",
            "name": "Kort nr 4",
            "shortName": "kort 4",
            "hasLight": True,
            "isEnabled": True,
            "tags": "Tennis;Hall",
            "sortNumber": 4,
            "type": 0,
            "groupName": None,
        },
    ],
}


@pytest.mark.asyncio
async def test_locations_for_club_returns_sorted(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        assert url.endswith("/api/v1/Clubs/c")
        return CLUB_DETAILS_WITH_LOCATIONS

    monkeypatch.setattr(ApiClient, "get", fake_get)
    svc = LocationsService(ApiClient(main_base="https://main"))
    locs = await svc.locations_for_club("c", access_token="t")
    assert [loc.id for loc in locs] == ["loc-1", "loc-2"]
    assert locs[0].name == "Kort nr 4"
    assert locs[1].name == "Badminton 2"


@pytest.mark.asyncio
async def test_locations_for_club_caches_names(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        return CLUB_DETAILS_WITH_LOCATIONS

    monkeypatch.setattr(ApiClient, "get", fake_get)
    svc = LocationsService(ApiClient(main_base="https://main"))
    await svc.locations_for_club("c", access_token="t")
    assert svc.name_for("loc-2") == "Badminton 2"
    assert svc.name_for("unknown") == "unknown"


@pytest.mark.asyncio
async def test_location_ids_for_club(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        return CLUB_DETAILS_WITH_LOCATIONS

    monkeypatch.setattr(ApiClient, "get", fake_get)
    svc = LocationsService(ApiClient(main_base="https://main"))
    ids = await svc.location_ids_for_club("c", access_token="t")
    assert sorted(ids) == ["loc-1", "loc-2"]


def test_name_lookup_from_known_bookings():
    svc = LocationsService(ApiClient(main_base=""))
    svc.remember_names_from_bookings(
        [
            {"locationId": "a", "locationName": "Badminton 1"},
            {"locationId": "b", "locationName": "Badminton 2"},
        ]
    )
    assert svc.name_for("a") == "Badminton 1"
    assert svc.name_for("unknown") == "unknown"


def test_remember_accepts_snake_case():
    svc = LocationsService(ApiClient(main_base=""))
    svc.remember_names_from_bookings([{"location_id": "z", "location_name": "Court Z"}])
    assert svc.name_for("z") == "Court Z"
