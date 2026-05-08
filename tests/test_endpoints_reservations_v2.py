import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.endpoints.reservations import ReservationsEndpoint
from twojtenis_mcp.tech_group import TechGroupResolver

SAMPLE_BOOKING = {
    "id": "b1",
    "clubId": "c",
    "clubName": "Klub",
    "locationId": "l",
    "locationName": "Court 1",
    "date": "2026-05-11",
    "startTime": "16:00:00",
    "endTime": "17:00:00",
    "price": 70.0,
    "isDeleted": False,
    "payment": {
        "id": "p",
        "status": "awaiting",
        "paidAmount": 0,
        "paymentDue": "2026-05-11T14:00:00",
        "discountType": "",
        "discountValue": 0,
        "amountToPay": 70,
        "initialAmount": 70,
    },
    "bookedFor": {
        "bookerHasUser": True,
        "bookerId": "bk",
        "cachedName": "S",
        "type": 0,
        "cachedEmail": "e",
        "cachedPhone": "+48",
    },
    "cancelUntil": "2026-05-10T16:00:00",
    "createdOn": "2026-05-07T21:14:25.5+00:00",
}


@pytest.mark.asyncio
async def test_get_reservations(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        if "/technical-groups" in url:
            return [{"id": "TG", "serviceUrl": "https://tech", "name": "TG"}]
        if "/bookings/my" in url:
            return [SAMPLE_BOOKING]
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main")
    ep = ReservationsEndpoint(client, TechGroupResolver(client))
    out = await ep.get_reservations(
        access_token="t", from_iso="2026-05-01", to_iso="2026-05-31"
    )
    assert len(out) == 1
    assert out[0]["id"] == "b1"
    assert out[0]["start_time"] == "16:00:00"


@pytest.mark.asyncio
async def test_delete_reservation(monkeypatch):
    seen: list[tuple[str, dict | None]] = []

    async def fake_get(self, url, *, access_token, params=None):
        if "/technical-groups" in url:
            return [{"id": "TG", "serviceUrl": "https://tech", "name": "TG"}]
        if "/bookings/my" in url:
            return [SAMPLE_BOOKING]
        if "/technical-group" in url:
            return {"id": "TG", "serviceUrl": "https://tech", "name": "TG"}
        raise AssertionError(url)

    async def fake_post(self, url, *, access_token, json=None):
        seen.append((url, json))
        return None

    monkeypatch.setattr(ApiClient, "get", fake_get)
    monkeypatch.setattr(ApiClient, "post", fake_post)
    client = ApiClient(main_base="https://main")
    ep = ReservationsEndpoint(client, TechGroupResolver(client))
    out = await ep.delete_reservation(booking_id="b1", access_token="t")
    assert out["success"] is True
    assert seen[0][0].endswith("/api/v1/Bookings/my/b1/cancel")
    assert seen[0][1] == {}


@pytest.mark.asyncio
async def test_get_reservation_details_returns_match(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        if "/technical-groups" in url:
            return [{"id": "TG", "serviceUrl": "https://tech", "name": "TG"}]
        if "/bookings/my" in url:
            return [SAMPLE_BOOKING]
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main")
    ep = ReservationsEndpoint(client, TechGroupResolver(client))
    found = await ep.get_reservation_details(booking_id="b1", access_token="t")
    assert found is not None
    assert found["id"] == "b1"
    missing = await ep.get_reservation_details(booking_id="nope", access_token="t")
    assert missing is None


@pytest.mark.asyncio
async def test_delete_reservation_when_missing(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        if "/technical-groups" in url:
            return [{"id": "TG", "serviceUrl": "https://tech", "name": "TG"}]
        if "/bookings/my" in url:
            return []
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    client = ApiClient(main_base="https://main")
    ep = ReservationsEndpoint(client, TechGroupResolver(client))
    out = await ep.delete_reservation(booking_id="ghost", access_token="t")
    assert out["success"] is False
