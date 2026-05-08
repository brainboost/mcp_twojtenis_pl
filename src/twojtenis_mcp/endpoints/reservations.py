from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..client import ApiClient
from ..models import ApiErrorException, Reservation
from ..tech_group import TechGroupResolver
from ..utils import encode_auth0_sub, to_iso_date
from .clubs import ClubsEndpoint


class ReservationsEndpoint:
    """All booking operations against the new tech-group API."""

    def __init__(self, client: ApiClient, resolver: TechGroupResolver) -> None:
        self._client = client
        self._resolver = resolver

    async def _user_tech_url(self, *, access_token: str) -> str:
        url = f"{self._client.main_base}/api/v1/Players/me/technical-groups"
        groups = await self._client.get(url, access_token=access_token) or []
        if not groups:
            raise ApiErrorException(
                "NO_TECH_GROUP",
                "user has no technical-group; cannot list reservations",
            )
        return groups[0]["serviceUrl"].rstrip("/")

    async def get_reservations(
        self, *, access_token: str, from_iso: str, to_iso: str
    ) -> list[dict[str, Any]]:
        tech = await self._user_tech_url(access_token=access_token)
        url = f"{tech}/api/v1/bookings/my"
        raw = (
            await self._client.get(
                url, access_token=access_token, params={"from": from_iso, "to": to_iso}
            )
            or []
        )
        return [Reservation.model_validate(r).model_dump(by_alias=False) for r in raw]

    async def get_reservation_details(
        self, *, booking_id: str, access_token: str
    ) -> dict[str, Any] | None:
        today = date.today()
        all_ = await self.get_reservations(
            access_token=access_token,
            from_iso=(today - timedelta(days=30)).isoformat(),
            to_iso=(today + timedelta(days=90)).isoformat(),
        )
        return next((r for r in all_ if r["id"] == booking_id), None)

    async def delete_reservation(
        self, *, booking_id: str, access_token: str
    ) -> dict[str, Any]:
        target = await self.get_reservation_details(
            booking_id=booking_id, access_token=access_token
        )
        if target is None:
            return {
                "success": False,
                "message": f"booking {booking_id} not found",
            }
        tech = await self._resolver.service_url_for_club(
            target["club_id"], access_token=access_token
        )
        url = f"{tech}/api/v1/Bookings/my/{booking_id}/cancel"
        await self._client.post(url, access_token=access_token, json={})
        return {"success": True, "message": "reservation cancelled"}

    async def _profile(self, *, access_token: str) -> dict[str, Any]:
        url = f"{self._client.main_base}/api/v1/Players/me"
        return await self._client.get(url, access_token=access_token)

    async def _player_in_club(
        self, *, club_id: str, auth0_sub: str, access_token: str
    ) -> dict[str, Any]:
        encoded = encode_auth0_sub(auth0_sub)
        url = f"{self._client.main_base}/api/v1/Clubs/{club_id}/players/{encoded}"
        return await self._client.get(url, access_token=access_token)

    async def _calculate_price(
        self,
        *,
        club_id: str,
        location_id: str,
        start: str,
        end: str,
        day_iso: str,
        access_token: str,
    ) -> dict[str, Any]:
        url = (
            f"{self._client.main_base}/api/v1/Clubs/{club_id}/actions/calculate-price"
        )
        body = {
            "clubId": club_id,
            "locationId": location_id,
            "start": start,
            "end": end,
            "days": [day_iso],
            "multiSportCardsUsed": 0,
            "medicoverCardsUsed": 0,
        }
        result = await self._client.post(url, access_token=access_token, json=body)
        prices = (result or {}).get("prices") or []
        if not prices or prices[0].get("failed"):
            raise ApiErrorException(
                "PRICE_CALCULATION_FAILED",
                f"calculate-price returned no usable price for {day_iso}",
            )
        return prices[0]

    @staticmethod
    def _normalize_time(t: str) -> str:
        return t if t.count(":") == 2 else f"{t}:00"

    async def _build_request_item(
        self,
        *,
        club_id: str,
        location_id: str,
        location_name: str,
        date: str,
        start_time: str,
        end_time: str,
        access_token: str,
    ) -> dict[str, Any]:
        day_iso = to_iso_date(date)
        start = self._normalize_time(start_time)
        end = self._normalize_time(end_time)
        price = await self._calculate_price(
            club_id=club_id,
            location_id=location_id,
            start=start,
            end=end,
            day_iso=day_iso,
            access_token=access_token,
        )
        return {
            "locationId": location_id,
            "startHour": start,
            "endHour": end,
            "date": day_iso,
            "price": price["price"],
            "checksum": price["checksum"],
            "locationName": location_name,
            "payment": {
                "amountToPay": price["price"],
                "discountType": "",
                "discountValue": 0,
                "paidAmount": 0,
                "initialAmount": price["initialPrice"],
                "paymentDue": f"{day_iso}T{start[:5]}:00.000Z",
                "status": "awaiting",
            },
            "multiSportCardsUsed": 0,
            "medicoverCardsUsed": 0,
        }

    async def make_reservation(
        self,
        *,
        club_id: str,
        location_id: str,
        location_name: str,
        date: str,
        start_time: str,
        end_time: str,
        access_token: str,
    ) -> dict[str, Any]:
        profile = await self._profile(access_token=access_token)
        player = await self._player_in_club(
            club_id=club_id, auth0_sub=profile["id"], access_token=access_token
        )
        request_item = await self._build_request_item(
            club_id=club_id,
            location_id=location_id,
            location_name=location_name,
            date=date,
            start_time=start_time,
            end_time=end_time,
            access_token=access_token,
        )

        clubs_ep = ClubsEndpoint(self._client)
        club_dict = await clubs_ep.get_club_by_id(club_id, access_token=access_token)
        club_name = club_dict["name"] if club_dict else ""
        booker_name = f"{profile['firstName']} {profile['lastName']}"

        body = {
            "requests": [request_item],
            "description": "",
            "bookerId": player["id"],
            "bookerName": booker_name,
            "bookerType": 0,
            "clubName": club_name,
            "comment": {
                "cachedAuthorName": booker_name,
                "text": "",
                "visibility": 2,
            },
            "bookerEmail": profile.get("email", ""),
            "bookerPhone": profile.get("phoneNumber", ""),
            "source": 0,
            "trainerProfileName": "undefined undefined",
        }

        tech = await self._resolver.service_url_for_club(
            club_id, access_token=access_token
        )
        url = f"{tech}/api/v1/Clubs/{club_id}/bookings"
        created = await self._client.post(url, access_token=access_token, json=body)
        if not created:
            raise ApiErrorException("BOOKING_FAILED", "server returned empty response")
        b0 = created[0] if isinstance(created, list) else created
        return {
            "success": True,
            "message": "reservation created",
            "reservation": {
                "id": b0["id"],
                "club_id": club_id,
                "location_id": location_id,
                "location_name": b0.get("locationName") or location_name,
                "date": b0["date"],
                "start_time": b0["startTime"],
                "end_time": b0["endTime"],
                "price": b0.get("price"),
            },
        }

    async def make_bulk_reservation(
        self,
        *,
        club_id: str,
        court_bookings: list[dict[str, Any]],
        access_token: str,
    ) -> dict[str, Any]:
        if not court_bookings:
            raise ApiErrorException(
                "VALIDATION_ERROR", "court_bookings cannot be empty"
            )
        profile = await self._profile(access_token=access_token)
        player = await self._player_in_club(
            club_id=club_id, auth0_sub=profile["id"], access_token=access_token
        )
        items = []
        for cb in court_bookings:
            items.append(
                await self._build_request_item(
                    club_id=club_id,
                    location_id=cb["location_id"],
                    location_name=cb["location_name"],
                    date=cb["date"],
                    start_time=cb["start_time"],
                    end_time=cb["end_time"],
                    access_token=access_token,
                )
            )
        clubs_ep = ClubsEndpoint(self._client)
        club_dict = await clubs_ep.get_club_by_id(club_id, access_token=access_token)
        booker_name = f"{profile['firstName']} {profile['lastName']}"
        body = {
            "requests": items,
            "description": "",
            "bookerId": player["id"],
            "bookerName": booker_name,
            "bookerType": 0,
            "clubName": club_dict["name"] if club_dict else "",
            "comment": {
                "cachedAuthorName": booker_name,
                "text": "",
                "visibility": 2,
            },
            "bookerEmail": profile.get("email", ""),
            "bookerPhone": profile.get("phoneNumber", ""),
            "source": 0,
            "trainerProfileName": "undefined undefined",
        }
        tech = await self._resolver.service_url_for_club(
            club_id, access_token=access_token
        )
        created = (
            await self._client.post(
                f"{tech}/api/v1/Clubs/{club_id}/bookings",
                access_token=access_token,
                json=body,
            )
            or []
        )
        return {
            "success": True,
            "message": f"created {len(created)} reservation(s)",
            "reservations": [
                {
                    "id": b["id"],
                    "location_id": b["locationId"],
                    "location_name": b.get("locationName"),
                    "date": b["date"],
                    "start_time": b["startTime"],
                    "end_time": b["endTime"],
                    "price": b.get("price"),
                }
                for b in created
            ],
        }

    async def delete_all_reservations(self, *, access_token: str) -> dict[str, Any]:
        today = date.today()
        bookings = await self.get_reservations(
            access_token=access_token,
            from_iso=today.isoformat(),
            to_iso=(today + timedelta(days=90)).isoformat(),
        )
        deleted: list[str] = []
        errors: list[dict[str, str]] = []
        for b in bookings:
            try:
                tech = await self._resolver.service_url_for_club(
                    b["club_id"], access_token=access_token
                )
                await self._client.post(
                    f"{tech}/api/v1/Bookings/my/{b['id']}/cancel",
                    access_token=access_token,
                    json={},
                )
                deleted.append(b["id"])
            except Exception as exc:
                errors.append({"booking_id": b["id"], "error": str(exc)})
        return {
            "success": not errors,
            "message": f"cancelled {len(deleted)} of {len(bookings)} reservations",
            "deleted_count": len(deleted),
            "deleted_booking_ids": deleted,
            "errors": errors,
        }
