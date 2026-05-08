from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .client import ApiClient
from .models import Location


class LocationsService:
    """Court (location) discovery for a club.

    The canonical source is the `locations` field in `GET /api/v1/Clubs/{id}` —
    each entry has `{id, name, shortName, hasLight, isEnabled, tags, sortNumber,
    type, groupName}`. We expose that list directly and cache `id → name` for
    callers that have only a UUID in hand.
    """

    def __init__(self, client: ApiClient) -> None:
        self._client = client
        self._names: dict[str, str] = {}

    async def locations_for_club(
        self, club_id: str, *, access_token: str
    ) -> list[Location]:
        url = f"{self._client.main_base}/api/v1/Clubs/{club_id}"
        details = await self._client.get(url, access_token=access_token) or {}
        raw = details.get("locations") or []
        locations = [Location.model_validate(item) for item in raw]
        for loc in locations:
            self._names[loc.id] = loc.name
        return sorted(locations, key=lambda x: (x.sort_number, x.name))

    async def location_ids_for_club(
        self, club_id: str, *, access_token: str
    ) -> list[str]:
        locations = await self.locations_for_club(club_id, access_token=access_token)
        return [loc.id for loc in locations]

    def remember_names_from_bookings(
        self, bookings: Iterable[dict[str, Any]]
    ) -> None:
        for b in bookings:
            lid = b.get("locationId") or b.get("location_id")
            name = b.get("locationName") or b.get("location_name")
            if lid and name:
                self._names[lid] = name

    def name_for(self, location_id: str) -> str:
        return self._names.get(location_id, location_id)
