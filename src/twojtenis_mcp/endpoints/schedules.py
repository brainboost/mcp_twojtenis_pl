from __future__ import annotations

from typing import Any

from ..client import ApiClient
from ..models import ApiErrorException
from ..tech_group import TechGroupResolver
from ..utils import to_iso_date


class SchedulesEndpoint:
    """Public schedule (occupied slots) and exclusions for a club on a given date."""

    def __init__(self, client: ApiClient, resolver: TechGroupResolver) -> None:
        self._client = client
        self._resolver = resolver

    async def get_club_schedule(
        self, *, club_id: str, date: str, access_token: str
    ) -> dict[str, Any]:
        try:
            iso = to_iso_date(date)
        except ValueError as exc:
            raise ApiErrorException("VALIDATION_ERROR", str(exc)) from exc

        tech = await self._resolver.service_url_for_club(
            club_id, access_token=access_token
        )
        bookings_url = f"{tech}/api/v1/Clubs/{club_id}/bookings/public"
        excludes_url = f"{tech}/api/v1/clubs/{club_id}/excludes/public"

        bookings = (
            await self._client.get(
                bookings_url, access_token=None, params={"from": iso, "to": iso}
            )
            or []
        )
        excludes = (
            await self._client.get(
                excludes_url, access_token=None, params={"date": iso}
            )
            or []
        )

        return {
            "success": True,
            "message": "schedule fetched",
            "data": {
                "club_id": club_id,
                "date": iso,
                "bookings": [
                    {
                        "id": b["id"],
                        "location_id": b["locationId"],
                        "date": b["date"],
                        "start_time": b["startTime"],
                        "end_time": b["endTime"],
                    }
                    for b in bookings
                ],
                "excludes": excludes,
            },
        }
