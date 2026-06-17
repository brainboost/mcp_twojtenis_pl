from __future__ import annotations

from typing import Any

from ..client import ApiClient
from ..models import Club
from ..router import ApiRouter


class ClubsEndpoint:
    """Read-only access to /api/v1/Clubs and per-club details."""

    def __init__(self, client: ApiClient, router: ApiRouter) -> None:
        self._client = client
        self._router = router

    async def list_clubs(self) -> list[dict[str, Any]]:
        url = self._router.catalog_url("/api/v1/Clubs")
        raw = await self._client.get(url, access_token=None) or []
        return [Club.model_validate(c).model_dump(by_alias=False) for c in raw]

    async def get_club_by_id(self, club_id: str) -> dict[str, Any] | None:
        clubs = await self.list_clubs()
        return next((c for c in clubs if c["id"] == club_id), None)

    async def get_club_details(self, club_id: str) -> dict[str, Any]:
        url = self._router.catalog_url(f"/api/v1/Clubs/{club_id}")
        return await self._client.get(url, access_token=None)

    async def get_club_settings(self, club_id: str) -> dict[str, Any]:
        url = self._router.catalog_url(f"/api/v1/Clubs/{club_id}/settings")
        return await self._client.get(url, access_token=None)
