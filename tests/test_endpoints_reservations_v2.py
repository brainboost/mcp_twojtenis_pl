import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.endpoints.reservations import ReservationsEndpoint
from twojtenis_mcp.router import ApiRouter
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
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main", resolver=resolver)
    ep = ReservationsEndpoint(client, router)
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
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main", resolver=resolver)
    ep = ReservationsEndpoint(client, router)
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
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main", resolver=resolver)
    ep = ReservationsEndpoint(client, router)
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
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main", resolver=resolver)
    ep = ReservationsEndpoint(client, router)
    out = await ep.delete_reservation(booking_id="ghost", access_token="t")
    assert out["success"] is False


@pytest.mark.asyncio
async def test_delete_all(monkeypatch):
    cancels: list[str] = []

    async def fake_get(self, url, *, access_token, params=None):
        if "/technical-groups" in url:
            return [{"id": "TG", "serviceUrl": "https://tech", "name": "TG"}]
        if "/bookings/my" in url:
            return [
                {**SAMPLE_BOOKING, "id": "b1"},
                {**SAMPLE_BOOKING, "id": "b2"},
            ]
        if "/technical-group" in url:
            return {"id": "TG", "serviceUrl": "https://tech", "name": "TG"}
        raise AssertionError(url)

    async def fake_post(self, url, *, access_token, json=None):
        cancels.append(url)
        return None

    monkeypatch.setattr(ApiClient, "get", fake_get)
    monkeypatch.setattr(ApiClient, "post", fake_post)
    client = ApiClient(main_base="https://main")
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main", resolver=resolver)
    ep = ReservationsEndpoint(client, router)
    out = await ep.delete_all_reservations(access_token="t")
    assert out["success"] is True
    assert out["deleted_count"] == 2
    assert sorted(out["deleted_booking_ids"]) == ["b1", "b2"]
    assert len(cancels) == 2


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
    return dict.fromkeys(
        (
            "phoneNo",
            "email",
            "www",
            "facebookProfile",
            "instagramProfile",
            "tikTokProfile",
            "twitterProfile",
        )
    )


PROFILE = {
    "firstName": "Sergei",
    "lastName": "V",
    "phoneNumber": "+48577",
    "email": "e",
    "id": "auth0|abc",
    "preferredRegionId": None,
    "yearOfBirth": 1971,
}
PLAYER_IN_CLUB = {
    "firstName": "Sergei",
    "lastName": "V",
    "phoneNumber": "+48577",
    "email": "e",
    "id": "booker-uuid",
    "type": 0,
    "playerId": "auth0|abc",
    "clubId": "c",
    "code": None,
    "isOnline": True,
    "isBlocked": False,
}
PRICE = {
    "clubId": "c",
    "locationId": "loc",
    "start": "16:00:00",
    "end": "17:00:00",
    "prices": [
        {
            "day": "2026-05-11",
            "price": 70.0,
            "initialPrice": 70.0,
            "checksum": "CHKSUM",
            "failed": False,
            "discount": 0,
            "multiSportCardsUsed": 0,
            "medicoverCardsUsed": 0,
        }
    ],
}
CLUB = {
    "id": "c",
    "name": "Klub",
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


@pytest.mark.asyncio
async def test_make_reservation(monkeypatch):
    captured: dict[str, dict] = {}

    async def fake_get(self, url, *, access_token, params=None):
        if url.endswith("/api/v1/Players/me"):
            return PROFILE
        if "/players/auth0%7Cabc" in url:
            return PLAYER_IN_CLUB
        if "/technical-group" in url:
            return {"id": "TG", "serviceUrl": "https://tech", "name": "TG"}
        if url.endswith("/api/v1/Clubs"):
            return [CLUB]
        raise AssertionError(url)

    async def fake_post(self, url, *, access_token, json=None):
        if json:
            captured[url] = json
        if "calculate-price" in url:
            return PRICE
        if url.endswith("/api/v1/Clubs/c/bookings"):
            return [{**SAMPLE_BOOKING, "id": "new-id"}]
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    monkeypatch.setattr(ApiClient, "post", fake_post)
    client = ApiClient(main_base="https://main")
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main", resolver=resolver)
    ep = ReservationsEndpoint(client, router)
    out = await ep.make_reservation(
        club_id="c",
        location_id="loc",
        location_name="Badminton 2",
        date="2026-05-11",
        start_time="16:00",
        end_time="17:00",
        access_token="t",
    )
    assert out["success"] is True
    assert out["reservation"]["id"] == "new-id"
    book_body = captured["https://tech/api/v1/Clubs/c/bookings"]
    assert book_body["bookerId"] == "booker-uuid"
    assert book_body["bookerName"] == "Sergei V"
    assert book_body["clubName"] == "Klub"
    assert book_body["requests"][0]["checksum"] == "CHKSUM"
    assert book_body["requests"][0]["locationId"] == "loc"
    assert book_body["requests"][0]["startHour"] == "16:00:00"
    assert book_body["requests"][0]["endHour"] == "17:00:00"
    assert book_body["requests"][0]["locationName"] == "Badminton 2"


@pytest.mark.asyncio
async def test_make_bulk_reservation_sends_one_post_with_two_items(monkeypatch):
    captured: dict[str, dict] = {}

    async def fake_get(self, url, *, access_token, params=None):
        if url.endswith("/api/v1/Players/me"):
            return PROFILE
        if "/players/auth0%7Cabc" in url:
            return PLAYER_IN_CLUB
        if "/technical-group" in url:
            return {"id": "TG", "serviceUrl": "https://tech", "name": "TG"}
        if url.endswith("/api/v1/Clubs"):
            return [CLUB]
        raise AssertionError(url)

    async def fake_post(self, url, *, access_token, json=None):
        if json:
            captured[url] = json
        if "calculate-price" in url:
            return PRICE
        if url.endswith("/api/v1/Clubs/c/bookings"):
            return [
                {**SAMPLE_BOOKING, "id": "b1", "startTime": "16:00:00"},
                {**SAMPLE_BOOKING, "id": "b2", "startTime": "17:00:00"},
            ]
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    monkeypatch.setattr(ApiClient, "post", fake_post)
    client = ApiClient(main_base="https://main")
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main", resolver=resolver)
    ep = ReservationsEndpoint(client, router)
    out = await ep.make_bulk_reservation(
        club_id="c",
        court_bookings=[
            {
                "location_id": "loc",
                "location_name": "Badminton 2",
                "date": "2026-05-11",
                "start_time": "16:00",
                "end_time": "17:00",
            },
            {
                "location_id": "loc",
                "location_name": "Badminton 2",
                "date": "2026-05-11",
                "start_time": "17:00",
                "end_time": "18:00",
            },
        ],
        access_token="t",
    )
    assert out["success"] is True
    assert len(out["reservations"]) == 2
    book_body = captured["https://tech/api/v1/Clubs/c/bookings"]
    assert len(book_body["requests"]) == 2
    assert book_body["requests"][0]["startHour"] == "16:00:00"
    assert book_body["requests"][1]["startHour"] == "17:00:00"


@pytest.mark.asyncio
async def test_make_bulk_reservation_rejects_empty():
    from twojtenis_mcp.models import ApiErrorException

    client = ApiClient(main_base="https://main")
    resolver = TechGroupResolver(client)
    router = ApiRouter(catalog_base="https://main", resolver=resolver)
    ep = ReservationsEndpoint(client, router)
    with pytest.raises(ApiErrorException) as ei:
        await ep.make_bulk_reservation(club_id="c", court_bookings=[], access_token="t")
    assert ei.value.code == "VALIDATION_ERROR"
