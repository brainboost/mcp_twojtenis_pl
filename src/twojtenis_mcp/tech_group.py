from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass

from .client import ApiClient
from .models import TechnicalGroup

logger = logging.getLogger(__name__)

_CACHE_TTL = float(os.environ.get("TWOJTENIS_TECH_GROUP_CACHE_TTL", "3600"))


@dataclass
class _CacheEntry:
    url: str
    expires_at: float  # time.monotonic()


class TechGroupResolver:
    """Resolves the per-club regional API base URL via /Clubs/{id}/technical-group.

    Each club is assigned to a "technical group" (e.g. TechGrp1 for Kraków) which
    declares its own service URL. The resolver caches results per-club with a TTL
    (default 3600 s, override via TWOJTENIS_TECH_GROUP_CACHE_TTL); call
    `invalidate(club_id)` to force a fresh lookup before the TTL expires.
    """

    def __init__(self, client: ApiClient) -> None:
        self._client = client
        self._cache: dict[str, _CacheEntry] = {}

    async def service_url_for_club(self, club_id: str, *, access_token: str) -> str:
        entry = self._cache.get(club_id)
        if entry is not None and time.monotonic() < entry.expires_at:
            return entry.url

        url = f"{self._client.main_base}/api/v1/Clubs/{club_id}/technical-group"
        last_exc: BaseException | None = None
        delays = [1, 2]  # sleep between attempt 1→2 and 2→3

        for attempt in range(3):
            try:
                raw = await self._client.get(url, access_token=access_token)
                tg = TechnicalGroup.model_validate(raw)
                resolved = tg.service_url.rstrip("/")
                self._cache[club_id] = _CacheEntry(
                    url=resolved,
                    expires_at=time.monotonic() + _CACHE_TTL,
                )
                return resolved
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < 2:
                    logger.warning(
                        "tech-group resolution attempt %d failed for club %s: %s",
                        attempt + 1,
                        club_id,
                        exc,
                    )
                    await asyncio.sleep(delays[attempt])

        logger.warning("tech-group resolution failed for club %s: %s", club_id, last_exc)
        raise last_exc  # type: ignore[misc]

    def invalidate(self, club_id: str | None = None) -> None:
        if club_id is None:
            self._cache.clear()
        else:
            self._cache.pop(club_id, None)
