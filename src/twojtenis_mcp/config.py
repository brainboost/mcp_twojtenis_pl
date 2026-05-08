from __future__ import annotations

import os


class Config:
    """Configuration with environment variable overrides."""

    @property
    def main_api_url(self) -> str:
        return os.getenv(
            "TWOJTENIS_MAIN_API_URL",
            "https://app-twojtenis-api-p-weu.azurewebsites.net",
        )

    @property
    def request_timeout(self) -> int:
        return int(os.getenv("TWOJTENIS_REQUEST_TIMEOUT", "30"))

    @property
    def auth0_domain(self) -> str:
        return os.getenv("AUTH0_DOMAIN", "twojtenis.eu.auth0.com")

    @property
    def auth0_client_id(self) -> str:
        return os.getenv("AUTH0_CLIENT_ID", "86BsGMVf8imqTkuKVkxeW2FalNALsO4y")

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
