from __future__ import annotations

from .client import ApiClient
from .models import TechnicalGroup


class TechGroupResolver:
    """Resolves the per-club regional API base URL via /Clubs/{id}/technical-group.

    Each club is assigned to a "technical group" (e.g. TechGrp1 for Kraków) which
    declares its own service URL. The resolver caches results per-club for the
    lifetime of the process; call `invalidate(club_id)` if a club's group changes.
    """

    def __init__(self, client: ApiClient) -> None:
        self._client = client
        self._cache: dict[str, str] = {}

    async def service_url_for_club(self, club_id: str, *, access_token: str) -> str:
        if club_id in self._cache:
            return self._cache[club_id]
        url = f"{self._client.main_base}/api/v1/Clubs/{club_id}/technical-group"
        raw = await self._client.get(url, access_token=access_token)
        tg = TechnicalGroup.model_validate(raw)
        self._cache[club_id] = tg.service_url.rstrip("/")
        return self._cache[club_id]

    def invalidate(self, club_id: str | None = None) -> None:
        if club_id is None:
            self._cache.clear()
        else:
            self._cache.pop(club_id, None)
