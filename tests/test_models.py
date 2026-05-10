from twojtenis_mcp.models import (
    ApiErrorException,
    Club,
    Reservation,
)


def test_club_parses_real_payload():
    raw = {
        "id": "b8431bee-80fe-435d-9f10-1f710a9ec003",
        "name": "Klub Testowy",
        "address": {
            "line": "Rynek Główny",
            "city": "Kraków",
            "region": "Małopolskie",
            "postalCode": "31-042",
            "latitude": 50.0619,
            "longitude": 19.9368,
        },
        "contactInfo": {
            "phoneNo": None,
            "email": None,
            "www": "https://x",
            "facebookProfile": None,
            "instagramProfile": None,
            "tikTokProfile": None,
            "twitterProfile": None,
        },
        "logoUrl": "https://x/logo.svg",
        "bannerUrl": None,
        "priceMin": 110.00,
        "priceMax": 160.00,
        "locationsCount": 3,
        "openHours": {
            "monday": {"from": "07:00:00", "to": "23:00:00"},
            "tuesday": {"from": "07:00:00", "to": "23:00:00"},
            "wednesday": {"from": "07:00:00", "to": "23:00:00"},
            "thursday": {"from": "07:00:00", "to": "23:00:00"},
            "friday": {"from": "07:00:00", "to": "23:00:00"},
            "saturday": {"from": "07:00:00", "to": "23:00:00"},
            "sunday": {"from": "07:00:00", "to": "23:00:00"},
        },
        "isSmartTennisPartner": False,
        "multiSportDiscount": 15.00,
        "medicoverDiscount": 15.00,
    }
    c = Club.model_validate(raw)
    assert c.id == "b8431bee-80fe-435d-9f10-1f710a9ec003"
    assert c.address.city == "Kraków"
    assert c.open_hours.monday.from_ == "07:00:00"
    assert c.locations_count == 3


def test_reservation_parses_my_bookings_payload():
    raw = {
        "bookedBy": "auth0|abc",
        "locationName": "Badminton 2",
        "clubName": "Błonia",
        "bookedFor": {
            "bookerHasUser": True,
            "bookerId": "u",
            "cachedName": "S",
            "type": 0,
            "cachedEmail": "e",
            "cachedPhone": "+48",
        },
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
        "isDeleted": False,
        "createdBy": "S",
        "createdOn": "2026-05-07T21:14:25.5+00:00",
        "cancelUntil": "2026-05-10T16:00:00",
        "clubId": "c",
        "date": "2026-05-11",
        "startTime": "16:00:00",
        "endTime": "17:00:00",
        "locationId": "l",
        "id": "b",
        "price": 70.00,
    }
    r = Reservation.model_validate(raw)
    assert r.id == "b"
    assert r.location_name == "Badminton 2"
    assert r.start_time == "16:00:00"
    assert r.payment.amount_to_pay == 70


def test_api_error_exception_carries_code_message_details():
    exc = ApiErrorException("X_CODE", "msg", {"k": 1})
    assert exc.code == "X_CODE"
    assert exc.message == "msg"
    assert exc.details == {"k": 1}
    assert str(exc) == "msg"
