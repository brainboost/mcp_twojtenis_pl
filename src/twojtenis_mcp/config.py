from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class Config:
    """Configuration with environment variable overrides."""

    @property
    def catalog_api_url(self) -> str:
        if val := os.environ.get("TWOJTENIS_CATALOG_API_URL"):
            return val
        if val := os.environ.get("TWOJTENIS_MAIN_API_URL"):
            logger.warning(
                "TWOJTENIS_MAIN_API_URL is deprecated; set TWOJTENIS_CATALOG_API_URL instead"
            )
            return val
        raise KeyError("TWOJTENIS_CATALOG_API_URL environment variable is required")

    @property
    def main_api_url(self) -> str:
        return os.environ["TWOJTENIS_MAIN_API_URL"]

    @property
    def request_timeout(self) -> int:
        return int(os.getenv("TWOJTENIS_REQUEST_TIMEOUT", "30"))

    @property
    def auth0_domain(self) -> str:
        return os.getenv("AUTH0_DOMAIN", "twojtenis.eu.auth0.com")

    @property
    def auth0_client_id(self) -> str:
        return os.environ["AUTH0_CLIENT_ID"]

    @property
    def auth0_audience(self) -> str:
        return os.getenv("AUTH0_AUDIENCE", "https://api.twojetenis.pl")

    @property
    def auth0_redirect_uri(self) -> str:
        return os.getenv("AUTH0_REDIRECT_URI", "https://app.twojtenis.pl")

    @property
    def auth0_scope(self) -> str:
        return os.getenv("AUTH0_SCOPE", "openid profile email offline_access")

    @property
    def auth0_browser_headless(self) -> bool:
        return os.getenv("AUTH0_BROWSER_HEADLESS", "true").lower() != "false"

    @property
    def auth0_browser_timeout(self) -> int:
        return int(os.getenv("AUTH0_BROWSER_TIMEOUT", "60"))

    @property
    def auth0_browser_executable_path(self) -> str | None:
        return os.getenv("AUTH0_BROWSER_EXECUTABLE_PATH") or None


config = Config()
