import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.endpoints.clubs import ClubsEndpoint
from twojtenis_mcp.router import ApiRouter
from twojtenis_mcp.tech_group import TechGroupResolver


def _open_hours_all_day():
    return {
        d: {"from": "07:00:00", "to": "23:00:00"}
        for d in (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
    }


def _empty_contact():
    return {
        k: None
        for k in (
            "phoneNo",
            "email",
            "www",
            "facebookProfile",
            "instagramProfile",
            "tikTokProfile",
            "twitterProfile",
        )
    }


@pytest.mark.asyncio
async def test_list_clubs_returns_dicts(monkeypatch):
    sample = [
        {
            "id": "u1",
            "name": "Test",
            "address": {
                "line": "a",
                "city": "Kr",
                "region": "M",
                "postalCode": "1",
                "latitude": 1.0,
                "longitude": 2.0,
            },
            "contactInfo": _empty_contact(),
            "logoUrl": None,
            "bannerUrl": None,
            "priceMin": 50,
            "priceMax": 120,
            "locationsCount": 2,
            "openHours": _open_hours_all_day(),
            "isSmartTennisPartner": False,
            "multiSportDiscount": 15,
            "medicoverDiscount": 15,
        }
    ]

    async def fake_get(self, url, *, access_token, params=None):
        assert url.endswith("/api/v1/Clubs")
        return sample

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main")
    router = ApiRouter(catalog_base="https://main", resolver=TechGroupResolver(client))
    ep = ClubsEndpoint(client, router)
    clubs = await ep.list_clubs(access_token="tok")
    assert clubs[0]["id"] == "u1"
    assert clubs[0]["name"] == "Test"


@pytest.mark.asyncio
async def test_get_club_by_id(monkeypatch):
    sample = [
        {
            "id": "u1",
            "name": "X",
            "address": {
                "line": "",
                "city": "",
                "region": "",
                "postalCode": "",
                "latitude": 0,
                "longitude": 0,
            },
            "contactInfo": _empty_contact(),
            "logoUrl": None,
            "bannerUrl": None,
            "priceMin": 0,
            "priceMax": 0,
            "locationsCount": 0,
            "openHours": _open_hours_all_day(),
            "isSmartTennisPartner": False,
            "multiSportDiscount": None,
            "medicoverDiscount": None,
        }
    ]

    async def fake_get(self, url, *, access_token, params=None):
        if url.endswith("/api/v1/Clubs"):
            return sample
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main")
    router = ApiRouter(catalog_base="https://main", resolver=TechGroupResolver(client))
    ep = ClubsEndpoint(client, router)
    club = await ep.get_club_by_id("u1", access_token="t")
    assert club is not None
    assert club["id"] == "u1"
    assert await ep.get_club_by_id("missing", access_token="t") is None


@pytest.mark.asyncio
async def test_get_club_details_passthrough(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        assert url.endswith("/api/v1/Clubs/abc")
        return {"owner": {}, "priceLists": [], "exceptions": []}

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main")
    router = ApiRouter(catalog_base="https://main", resolver=TechGroupResolver(client))
    ep = ClubsEndpoint(client, router)
    out = await ep.get_club_details("abc", access_token="t")
    assert out == {"owner": {}, "priceLists": [], "exceptions": []}


@pytest.mark.asyncio
async def test_get_club_settings_passthrough(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        assert url.endswith("/api/v1/Clubs/abc/settings")
        return {"maxDaysInAdvance": 7, "maxHoursForCancel": 24}

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main")
    router = ApiRouter(catalog_base="https://main", resolver=TechGroupResolver(client))
    ep = ClubsEndpoint(client, router)
    out = await ep.get_club_settings("abc", access_token="t")
    assert out["maxDaysInAdvance"] == 7
