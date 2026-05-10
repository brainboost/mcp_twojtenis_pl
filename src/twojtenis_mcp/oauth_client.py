"""Auth0 token acquisition for api.twojetenis.pl."""

import base64
import hashlib
import os
import secrets
import sys
import time
from typing import Any

import httpx

from .config import config
from .models import ApiErrorException
from .oauth_browser import OAuthBrowserError

# Module-level reference to the browser login function.
# Lazily populated on first real call; tests can replace this directly.
perform_browser_login = None


class OAuthClient:
    """Handles Auth0 token acquisition for api.twojetenis.pl."""

    def __init__(self) -> None:
        self._token_url = f"https://{config.auth0_domain}/oauth/token"

    async def login(self, email: str, password: str) -> dict[str, Any]:
        """Drive the Auth0 Universal Login form via Playwright and exchange
        the resulting authorization code for tokens.

        Returns:
            {
              "access_token": "<jwt>",
              "refresh_token": "<token>" | None,
              "expires_at": <epoch_seconds>,
              "token_type": "Bearer",
              "scope": "openid profile email offline_access",
              "id_token": "<jwt>" | None,
            }

        Raises:
            ApiErrorException with codes:
                OAUTH_INVALID_CREDENTIALS  - login form rejected credentials
                OAUTH_PLAYWRIGHT_REQUIRED  - playwright not installed
                OAUTH_BROWSER_TIMEOUT      - flow exceeded timeout
                OAUTH_NETWORK_ERROR        - connection issue with Auth0
                OAUTH_UNEXPECTED           - everything else
        """
        _module = sys.modules[__name__]
        _fn = _module.perform_browser_login  # type: ignore[attr-defined]

        if _fn is None:
            try:
                from .oauth_browser import perform_browser_login as _pbf

                _module.perform_browser_login = _pbf  # ty:ignore[unresolved-attribute]
                _fn = _pbf
            except ImportError as exc:
                raise ApiErrorException(
                    code="OAUTH_PLAYWRIGHT_REQUIRED",
                    message=(
                        "Playwright is not installed. "
                        "Run: uv pip install -e '.[browser-auth]' && "
                        f"uv run playwright install chromium. Error: {exc}"
                    ),
                ) from exc

        verifier, challenge = self._pkce_pair()
        state = self._random_state()
        nonce = self._random_state()

        try:
            code = await _fn(
                domain=config.auth0_domain,
                client_id=config.auth0_client_id,
                audience=config.auth0_audience,
                redirect_uri=config.auth0_redirect_uri,
                scope=config.auth0_scope,
                code_challenge=challenge,
                state=state,
                nonce=nonce,
                email=email,
                password=password,
                headless=config.auth0_browser_headless,
                timeout_s=config.auth0_browser_timeout,
                executable_path=config.auth0_browser_executable_path or None,
            )
        except ImportError as exc:
            raise ApiErrorException(
                code="OAUTH_PLAYWRIGHT_REQUIRED",
                message=f"Playwright is not installed. {exc}",
            ) from exc
        except OAuthBrowserError as exc:
            if exc.kind == "invalid_credentials":
                raise ApiErrorException(
                    code="OAUTH_INVALID_CREDENTIALS",
                    message=str(exc),
                ) from exc
            if exc.kind == "timeout":
                raise ApiErrorException(
                    code="OAUTH_BROWSER_TIMEOUT",
                    message=str(exc),
                ) from exc
            raise ApiErrorException(
                code="OAUTH_UNEXPECTED",
                message=str(exc),
            ) from exc
        except httpx.RequestError as exc:
            raise ApiErrorException(
                code="OAUTH_NETWORK_ERROR",
                message=f"Network error contacting Auth0: {exc}",
            ) from exc

        return await self._exchange_code(code=code, code_verifier=verifier)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """POST grant_type=refresh_token. Same return shape as login().
        Pure HTTP — no browser involved.

        Raises:
            ApiErrorException with codes:
                OAUTH_INVALID_CREDENTIALS  - refresh token expired/invalid
                OAUTH_NETWORK_ERROR        - connection issue
                OAUTH_UNEXPECTED           - anything else
        """
        body = {
            "grant_type": "refresh_token",
            "client_id": config.auth0_client_id,
            "refresh_token": refresh_token,
        }

        try:
            async with httpx.AsyncClient(timeout=config.request_timeout) as client:
                response = await client.post(self._token_url, data=body)
        except httpx.RequestError as exc:
            raise ApiErrorException(
                code="OAUTH_NETWORK_ERROR",
                message=f"Network error contacting Auth0: {exc}",
            ) from exc

        payload = response.json()

        if response.status_code >= 400:
            error = payload.get("error", "")
            description = payload.get("error_description", str(payload))
            if error in ("invalid_grant", "invalid_token"):
                raise ApiErrorException(
                    code="OAUTH_INVALID_CREDENTIALS",
                    message=f"Refresh token invalid or expired: {description}",
                )
            raise ApiErrorException(
                code="OAUTH_UNEXPECTED",
                message=f"Auth0 token refresh failed ({response.status_code}): {description}",
            )

        return self._parse_token_response(payload)

    @staticmethod
    def _pkce_pair() -> tuple[str, str]:
        """Return (verifier, challenge) for PKCE S256.

        verifier: 43-char URL-safe base64 (32 random bytes, no padding).
        challenge: base64url(sha256(verifier_bytes)).rstrip('=')
        """
        verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return verifier, challenge

    @staticmethod
    def _random_state() -> str:
        """Return a 16-byte URL-safe random string."""
        return secrets.token_urlsafe(16)

    async def _exchange_code(
        self,
        code: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        """POST to /oauth/token with grant_type=authorization_code.

        Returns the token dict with expires_at computed from expires_in.
        """
        body = {
            "grant_type": "authorization_code",
            "client_id": config.auth0_client_id,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": config.auth0_redirect_uri,
        }

        try:
            async with httpx.AsyncClient(timeout=config.request_timeout) as client:
                response = await client.post(self._token_url, data=body)
        except httpx.RequestError as exc:
            raise ApiErrorException(
                code="OAUTH_NETWORK_ERROR",
                message=f"Network error exchanging auth code: {exc}",
            ) from exc

        payload = response.json()

        if response.status_code >= 400:
            error = payload.get("error", "")
            description = payload.get("error_description", str(payload))
            if error in ("invalid_grant", "access_denied"):
                raise ApiErrorException(
                    code="OAUTH_INVALID_CREDENTIALS",
                    message=f"Auth code exchange rejected: {description}",
                )
            raise ApiErrorException(
                code="OAUTH_UNEXPECTED",
                message=f"Auth0 token exchange failed ({response.status_code}): {description}",
            )

        return self._parse_token_response(payload)

    @staticmethod
    def _parse_token_response(payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize a raw /oauth/token response into a stable dict."""
        return {
            "access_token": payload["access_token"],
            "refresh_token": payload.get("refresh_token"),
            "id_token": payload.get("id_token"),
            "expires_at": int(time.time()) + int(payload["expires_in"]),
            "token_type": payload.get("token_type", "Bearer"),
            "scope": payload.get("scope", ""),
        }
