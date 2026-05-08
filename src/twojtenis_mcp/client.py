from __future__ import annotations

from typing import Any, Mapping

import httpx

from .models import ApiErrorException


class ApiClient:
    """Thin async HTTP wrapper for the new TwojTenis JSON API.

    Callers pass a fully-qualified URL plus the `access_token`. The client does
    not own host routing — endpoints decide whether to hit the main API host
    or a per-club tech-group host (resolved via `TechGroupResolver`).
    """

    def __init__(self, main_base: str, timeout: float = 30.0) -> None:
        self.main_base = main_base.rstrip("/")
        self._timeout = timeout

    async def get(
        self,
        url: str,
        *,
        access_token: str | None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._send("GET", url, access_token, params=params)

    async def post(
        self,
        url: str,
        *,
        access_token: str | None,
        json: Any | None = None,
    ) -> Any:
        return await self._send("POST", url, access_token, json=json)

    async def _send(
        self,
        method: str,
        url: str,
        access_token: str | None,
        params: Mapping[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        headers: dict[str, str] = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if json is not None:
            headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.request(
                    method, url, headers=headers, params=params, json=json
                )
        except httpx.RequestError as exc:
            raise ApiErrorException(
                "REQUEST_FAILED", f"network error: {exc}"
            ) from exc

        if resp.status_code == 401:
            raise ApiErrorException(
                "AUTHENTICATION_REQUIRED",
                "token rejected by server",
                {"status": 401, "body": resp.text[:500]},
            )
        if resp.status_code == 403:
            raise ApiErrorException(
                "FORBIDDEN",
                "operation not permitted",
                {"status": 403, "body": resp.text[:500]},
            )
        if resp.status_code >= 400:
            raise ApiErrorException(
                "HTTP_ERROR",
                f"HTTP {resp.status_code}",
                {"status": resp.status_code, "body": resp.text[:500]},
            )

        if resp.status_code == 204 or not resp.content:
            return None
        ct = resp.headers.get("content-type", "")
        if "application/json" in ct:
            return resp.json()
        return resp.text
