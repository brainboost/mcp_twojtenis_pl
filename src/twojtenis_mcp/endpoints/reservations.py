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
