from __future__ import annotations

from typing import Any

from ..client import ApiClient
from ..models import Club


class ClubsEndpoint:
    """Read-only access to /api/v1/Clubs and per-club details."""

    def __init__(self, client: ApiClient) -> None:
        self._client = client

    async def list_clubs(self, *, access_token: str) -> list[dict[str, Any]]:
        url = f"{self._client.main_base}/api/v1/Clubs"
        raw = await self._client.get(url, access_token=access_token) or []
        return [Club.model_validate(c).model_dump(by_alias=False) for c in raw]

    async def get_club_by_id(
        self, club_id: str, *, access_token: str
    ) -> dict[str, Any] | None:
        clubs = await self.list_clubs(access_token=access_token)
        return next((c for c in clubs if c["id"] == club_id), None)

    async def get_club_details(
        self, club_id: str, *, access_token: str
    ) -> dict[str, Any]:
        url = f"{self._client.main_base}/api/v1/Clubs/{club_id}"
        return await self._client.get(url, access_token=access_token)

    async def get_club_settings(
        self, club_id: str, *, access_token: str
    ) -> dict[str, Any]:
        url = f"{self._client.main_base}/api/v1/Clubs/{club_id}/settings"
        return await self._client.get(url, access_token=access_token)
