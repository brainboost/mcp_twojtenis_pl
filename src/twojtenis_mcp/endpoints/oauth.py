from typing import Any

from ..oauth_client import OAuthClient


class OAuthEndpoint:
    def __init__(self) -> None:
        self.client = OAuthClient()

    async def login(self, email: str, password: str) -> dict[str, Any]:
        return await self.client.login(email, password)

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        return await self.client.refresh(refresh_token)


oauth_endpoint = OAuthEndpoint()
