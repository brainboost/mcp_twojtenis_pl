from __future__ import annotations

from typing import Any

from ..availability import build_availability
from ..client import ApiClient
from ..locations import LocationsService
from ..models import ApiErrorException
from ..router import ApiRouter
from ..utils import to_iso_date


class SchedulesEndpoint:
    """Per-court availability grid for one club + date.

    Internally fans out to:
      - GET /api/v1/Clubs/{id}                 (cached via LocationsService)
      - GET {tech}/api/v1/Clubs/{id}/bookings/public?from=&to=
      - GET {tech}/api/v1/clubs/{id}/excludes/public?date=

    Then walks each court's open window in 30-minute slots and marks each as
    available iff no booking or exclude overlaps it.
    """

    def __init__(
        self,
        client: ApiClient,
        router: ApiRouter,
        locations: LocationsService,
    ) -> None:
        self._client = client
        self._router = router
        self._locations = locations

    async def get_club_schedule(self, *, club_id: str, date: str) -> dict[str, Any]:
        try:
            iso = to_iso_date(date)
        except ValueError as exc:
            raise ApiErrorException("VALIDATION_ERROR", str(exc)) from exc

        details = await self._locations.get_club_details(club_id)
        locations = details.get("locations") or []
        open_hours = details.get("openHours") or {}

        bookings = (
            await self._router.booking_get(
                club_id,
                f"/api/v1/Clubs/{club_id}/bookings/public",
                client=self._client,
                params={"from": iso, "to": iso},
            )
            or []
        )
        excludes = (
            await self._router.booking_get(
                club_id,
                f"/api/v1/clubs/{club_id}/excludes/public",
                client=self._client,
                params={"date": iso},
            )
            or []
        )

        availability = build_availability(
            iso_date=iso,
            locations=locations,
            open_hours=open_hours,
            bookings=bookings,
            excludes=excludes,
        )

        return {
            "success": True,
            "message": "schedule fetched",
            "data": {
                "club_id": club_id,
                "date": iso,
                "availability": availability,
            },
        }
