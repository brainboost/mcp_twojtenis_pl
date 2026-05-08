from __future__ import annotations

from typing import Any, Iterable

from .client import ApiClient


class LocationsService:
    """Court (location) UUID + name resolution.

    The new API does not expose a dedicated locations endpoint. The canonical
    set of court UUIDs for a club is derivable from the union of
    `priceLists[*].rules[*].locations` in /Clubs/{id}. Court display names like
    "Badminton 2" are not present in any list endpoint we have observed; we
    learn them opportunistically from /bookings/my responses (which include
    `locationName` per booking) and fall back to the bare UUID otherwise.
    """

    def __init__(self, client: ApiClient) -> None:
        self._client = client
        self._names: dict[str, str] = {}

    async def location_ids_for_club(
        self, club_id: str, *, access_token: str
    ) -> list[str]:
        url = f"{self._client.main_base}/api/v1/Clubs/{club_id}"
        details = await self._client.get(url, access_token=access_token) or {}
        ids: set[str] = set()
        for pl in details.get("priceLists", []):
            for rule in pl.get("rules", []):
                ids.update(rule.get("locations", []))
        return sorted(ids)

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
