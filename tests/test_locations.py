import pytest

from twojtenis_mcp.client import ApiClient
from twojtenis_mcp.locations import LocationsService


@pytest.mark.asyncio
async def test_collect_uuids_from_pricelists(monkeypatch):
    async def fake_get(self, url, *, access_token, params=None):
        if url.endswith("/api/v1/Clubs/c"):
            return {
                "owner": {},
                "priceLists": [
                    {
                        "id": "pl",
                        "name": "x",
                        "visible": True,
                        "rules": [
                            {
                                "id": "r1",
                                "locations": ["a", "b"],
                                "startDay": 1,
                                "endDay": 5,
                                "startHour": "07:00:00",
                                "endHour": "15:00:00",
                                "price": 50,
                                "onlinePaymentOption": 1,
                            },
                            {
                                "id": "r2",
                                "locations": ["b", "c"],
                                "startDay": 1,
                                "endDay": 5,
                                "startHour": "15:00:00",
                                "endHour": "23:00:00",
                                "price": 80,
                                "onlinePaymentOption": 1,
                            },
                        ],
                    }
                ],
                "exceptions": [],
            }
        raise AssertionError(url)

    monkeypatch.setattr(ApiClient, "get", fake_get)
    svc = LocationsService(ApiClient(main_base="https://main"))
    ids = await svc.location_ids_for_club("c", access_token="t")
    assert sorted(ids) == ["a", "b", "c"]


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
