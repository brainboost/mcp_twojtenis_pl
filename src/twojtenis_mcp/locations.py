from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .client import ApiClient
from .models import Location
from .router import ApiRouter


class LocationsService:
    """Court (location) discovery for a club.

    The canonical source is the `locations` field in `GET /api/v1/Clubs/{id}` —
    each entry has `{id, name, shortName, hasLight, isEnabled, tags, sortNumber,
    type, groupName}`. We expose that list directly and cache `id → name` for
    callers that have only a UUID in hand.
    """

    def __init__(self, client: ApiClient, router: ApiRouter) -> None:
        self._client = client
        self._router = router
        self._names: dict[str, str] = {}
        self._details_cache: dict[str, dict[str, Any]] = {}

    async def get_club_details(self, club_id: str) -> dict[str, Any]:
        """Return the cached `/api/v1/Clubs/{id}` response. One fetch per process per club."""
        cached = self._details_cache.get(club_id)
        if cached is not None:
            return cached
        url = self._router.catalog_url(f"/api/v1/Clubs/{club_id}")
        details = await self._client.get(url, access_token=None) or {}
        self._details_cache[club_id] = details
        return details

    def invalidate_club(self, club_id: str | None = None) -> None:
        if club_id is None:
            self._details_cache.clear()
        else:
            self._details_cache.pop(club_id, None)

    async def locations_for_club(
        self,
        club_id: str,
        sport: str | None = None,
    ) -> list[Location]:
        """Return courts for a club, sorted by `sort_number, name`.

        If `sport` is provided, only locations whose derived `sport` field
        matches (case-insensitive) are returned. See `models.SPORT_BY_TYPE`
        for known values: "tennis", "badminton", "padel", "squash",
        "table_tennis", "fitness", "bowling", "football", "multi".
        """
        details = await self.get_club_details(club_id)
        raw = details.get("locations") or []
        locations = [Location.model_validate(item) for item in raw]
        for loc in locations:
            self._names[loc.id] = loc.name
        locations.sort(key=lambda x: (x.sort_number, x.name))
        if sport is not None:
            wanted = sport.strip().lower()
            locations = [
                loc for loc in locations if (loc.sport or "").lower() == wanted
            ]
        return locations

    async def location_ids_for_club(
        self, club_id: str, *, access_token: str
    ) -> list[str]:
        locations = await self.locations_for_club(club_id)
        return [loc.id for loc in locations]

    def remember_names_from_bookings(self, bookings: Iterable[dict[str, Any]]) -> None:
        for b in bookings:
            lid = b.get("locationId") or b.get("location_id")
            name = b.get("locationName") or b.get("location_name")
            if lid and name:
                self._names[lid] = name

    def name_for(self, location_id: str) -> str:
        return self._names.get(location_id, location_id)
