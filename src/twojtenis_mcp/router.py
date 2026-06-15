from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .models import ApiErrorException
from .tech_group import TechGroupResolver

if TYPE_CHECKING:
    from .client import ApiClient


class ApiRouter:
    """Central URL router for the two TwojTenis API hosts.

    - catalog_url(): Main catalog API (clubs, players, pricing, configuration)
    - booking_url(): Per-club regional booking API (bookings, schedule, excludes)
      resolved dynamically via TechGroupResolver with env-var override support.
    """

    def __init__(self, catalog_base: str, resolver: TechGroupResolver) -> None:
        self.catalog_base = catalog_base.rstrip("/")
        self._resolver = resolver

    def catalog_url(self, path: str) -> str:
        return f"{self.catalog_base}{path}"

    async def booking_url(self, club_id: str, path: str, *, access_token: str) -> str:
        club_key = club_id.replace("-", "_").upper()
        override = os.environ.get(f"TWOJTENIS_BOOKING_API_URL_{club_key}") or os.environ.get(
            "TWOJTENIS_BOOKING_API_URL"
        )
        if override:
            return f"{override.rstrip('/')}{path}"
        tech = await self._resolver.service_url_for_club(club_id, access_token=access_token)
        return f"{tech}{path}"

    async def booking_get(
        self,
        club_id: str,
        path: str,
        *,
        access_token: str | None,
        client: ApiClient,
        params=None,
    ) -> Any:
        """GET from the booking API. On 404, invalidates tech-group cache and retries once."""
        url = await self.booking_url(club_id, path, access_token=access_token or "")
        try:
            return await client.get(url, access_token=access_token, params=params)
        except ApiErrorException as exc:
            if exc.code == "HTTP_ERROR" and (exc.details or {}).get("status") == 404:
                club_key = club_id.replace("-", "_").upper()
                self._resolver.invalidate(club_id)
                url2 = await self.booking_url(club_id, path, access_token=access_token or "")
                if url2 == url:
                    raise ApiErrorException(
                        "BOOKING_URL_MISMATCH",
                        f"404 from {url!r}. Tech-group URL may be stale or wrong. "
                        f"Override with TWOJTENIS_BOOKING_API_URL_{club_key}=<correct_url>",
                        exc.details,
                    ) from exc
                return await client.get(url2, access_token=access_token, params=params)
            raise
