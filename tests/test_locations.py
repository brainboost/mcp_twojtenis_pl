import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.locations import LocationsService
from twojtenis_mcp.router import ApiRouter
from twojtenis_mcp.tech_group import TechGroupResolver

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
        {
            "id": "loc-3",
            "name": "Padel 1",
            "shortName": "P1",
            "hasLight": True,
            "isEnabled": True,
            "tags": "Padel;Outdoor",
            "sortNumber": 20,
            "type": 8,
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
    _client = ApiClient(main_base="https://main")
    svc = LocationsService(
        _client,
        ApiRouter(catalog_base="https://main", resolver=TechGroupResolver(_client)),
    )
    locs = await svc.locations_for_club("c")
    assert [loc.id for loc in locs] == ["loc-1", "loc-2", "loc-3"]
    assert locs[0].name == "Kort nr 4"
    assert locs[0].sport == "tennis"
    assert locs[1].sport == "badminton"
    assert locs[2].sport == "padel"


@pytest.mark.asyncio
async def test_locations_filters_by_sport(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        return CLUB_DETAILS_WITH_LOCATIONS

    monkeypatch.setattr(ApiClient, "get", fake_get)
    _client = ApiClient(main_base="https://main")
    svc = LocationsService(
        _client,
        ApiRouter(catalog_base="https://main", resolver=TechGroupResolver(_client)),
    )
    badminton = await svc.locations_for_club("c", sport="badminton")
    assert [loc.id for loc in badminton] == ["loc-2"]
    tennis = await svc.locations_for_club("c", sport="TENNIS")
    assert [loc.id for loc in tennis] == ["loc-1"]
    none = await svc.locations_for_club("c", sport="curling")
    assert none == []


def test_derive_sport_from_type_and_tags():
    from twojtenis_mcp.models import derive_sport

    assert derive_sport(0, "Tennis;Hard") == "tennis"
    assert derive_sport(1, "Badminton") == "badminton"
    assert derive_sport(8, "Padel") == "padel"
    # Unknown type falls back to tag scan
    assert derive_sport(99, "Squash") == "squash"
    # Polish football tag
    assert derive_sport(99, "PiłkaNożna;Boisko") == "football"
    # No tag, no known type
    assert derive_sport(99, None) is None
    assert derive_sport(99, "WeirdTag") is None


def test_location_serializes_with_sport_field():
    from twojtenis_mcp.models import Location

    loc = Location.model_validate(
        {
            "id": "x",
            "name": "Padel 1",
            "type": 8,
            "tags": "Padel;Outdoor",
        }
    )
    dumped = loc.model_dump(by_alias=False)
    assert dumped["sport"] == "padel"


@pytest.mark.asyncio
async def test_locations_for_club_caches_names(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        return CLUB_DETAILS_WITH_LOCATIONS

    monkeypatch.setattr(ApiClient, "get", fake_get)
    _client = ApiClient(main_base="https://main")
    svc = LocationsService(
        _client,
        ApiRouter(catalog_base="https://main", resolver=TechGroupResolver(_client)),
    )
    await svc.locations_for_club("c")
    assert svc.name_for("loc-2") == "Badminton 2"
    assert svc.name_for("unknown") == "unknown"


@pytest.mark.asyncio
async def test_location_ids_for_club(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        return CLUB_DETAILS_WITH_LOCATIONS

    monkeypatch.setattr(ApiClient, "get", fake_get)
    _client = ApiClient(main_base="https://main")
    svc = LocationsService(
        _client,
        ApiRouter(catalog_base="https://main", resolver=TechGroupResolver(_client)),
    )
    ids = await svc.location_ids_for_club("c", access_token="t")
    assert sorted(ids) == ["loc-1", "loc-2", "loc-3"]


def test_name_lookup_from_known_bookings():
    _client = ApiClient(main_base="")
    svc = LocationsService(
        _client, ApiRouter(catalog_base="", resolver=TechGroupResolver(_client))
    )
    svc.remember_names_from_bookings(
        [
            {"locationId": "a", "locationName": "Badminton 1"},
            {"locationId": "b", "locationName": "Badminton 2"},
        ]
    )
    assert svc.name_for("a") == "Badminton 1"
    assert svc.name_for("unknown") == "unknown"


def test_remember_accepts_snake_case():
    _client = ApiClient(main_base="")
    svc = LocationsService(
        _client, ApiRouter(catalog_base="", resolver=TechGroupResolver(_client))
    )
    svc.remember_names_from_bookings([{"location_id": "z", "location_name": "Court Z"}])
    assert svc.name_for("z") == "Court Z"
