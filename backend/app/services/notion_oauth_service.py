import os
from urllib.parse import urlencode

import httpx


class NotionOAuthService:
    def __init__(self):
        self.client_id = os.getenv("NOTION_CLIENT_ID")
        self.client_secret = os.getenv("NOTION_CLIENT_SECRET")
        self.redirect_uri = os.getenv("NOTION_REDIRECT_URI")
        self.auth_url = os.getenv("NOTION_AUTH_URL")
        self.token_url = "https://api.notion.com/v1/oauth/token"

        if not self.client_id:
            raise RuntimeError("NOTION_CLIENT_ID is not configured")

        if not self.client_secret:
            raise RuntimeError("NOTION_CLIENT_SECRET is not configured")

        if not self.redirect_uri:
            raise RuntimeError("NOTION_REDIRECT_URI is not configured")

        if not self.auth_url:
            raise RuntimeError("NOTION_AUTH_URL is not configured")

    def get_authorization_url(
        self,
        state: str,
    ) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "owner": "user",
            "state": state,
        }

        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
    ) -> dict:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                json=payload,
                auth=(
                    self.client_id,
                    self.client_secret,
                ),
            )

        if response.is_error:
            raise RuntimeError(
                f"Notion token exchange failed: "
                f"{response.status_code} "
                f"{response.text}"
            )

        return response.json()