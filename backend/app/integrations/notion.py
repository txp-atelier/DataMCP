from typing import Any
from datetime import datetime

import httpx
import os
import requests

from app.integrations.base import KnowledgeProvider
from app.services.integration_manager import IntegrationManager
from app.services.integration_secret_manager import (
    IntegrationSecretManager,
)


class NotionProvider(KnowledgeProvider):
    provider_name = "notion"

    def __init__(self):
        self.integration_manager = IntegrationManager()
        self.secret_manager = IntegrationSecretManager()
        self.base_url = "https://api.notion.com/v1"
        self.notion_version = "2026-03-11"
        self.parent_page_id = os.getenv(
            "NOTION_PARENT_PAGE_ID"
        )

    def _get_credentials(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        integrations = self.integration_manager.get_all(
            user_id
        )

        integration = None

        for item in integrations:
            if item.provider.value == self.provider_name:
                integration = item
                break

        if not integration:
            raise RuntimeError(
                "Notion integration not found"
            )

        if integration.status.value != "connected":
            raise RuntimeError(
                "Notion integration is not connected"
            )

        credentials = self.secret_manager.get(
            integration.id
        )

        if not credentials:
            raise RuntimeError(
                "Notion credentials not found"
            )

        return credentials

    def _headers(
        self,
        credentials: dict[str, Any],
    ) -> dict[str, str]:
        return {
            "Authorization": (
                f"Bearer {credentials['access_token']}"
            ),
            "Notion-Version": self.notion_version,
            "Content-Type": "application/json",
        }

    def _extract_title(
        self,
        item: dict[str, Any],
    ) -> str:
        properties = item.get("properties", {})

        for property_data in properties.values():
            if property_data.get("type") == "title":
                title_items = property_data.get(
                    "title",
                    [],
                )

                return "".join(
                    item.get("plain_text", "")
                    for item in title_items
                )

        return ""

    async def search(
        self,
        query: str,
        user_id: str,
    ) -> list[dict[str, Any]]:
        credentials = self._get_credentials(
            user_id
        )

        payload = {
            "query": query,
            "page_size": 20,
        }

        headers = self._headers(credentials)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/search",
                json=payload,
                headers=headers,
            )

        if response.is_error:
            raise RuntimeError(
                f"Notion search failed: "
                f"{response.status_code} "
                f"{response.text}"
            )

        data = response.json()

        results = []

        for item in data.get("results", []):
            results.append(
                {
                    "id": item.get("id"),
                    "object": item.get("object"),
                    "url": item.get("url"),
                    "title": self._extract_title(item),
                }
            )

        return results

    def _blocks_to_text(
        self,
        blocks: list[dict[str, Any]],
    ) -> str:
        lines = []

        for block in blocks:
            block_type = block.get("type")

            if not block_type:
                continue

            block_data = block.get(
                block_type,
                {},
            )

            rich_text = block_data.get(
                "rich_text",
                [],
            )

            text = "".join(
                item.get("plain_text", "")
                for item in rich_text
            )

            if text:
                lines.append(text)

        return "\n".join(lines)

    def _content_to_blocks(
        self,
        content: str,
    ) -> list[dict[str, Any]]:
        if not content:
            return []

        max_length = 2000

        chunks = [
            content[index:index + max_length]
            for index in range(
                0,
                len(content),
                max_length,
            )
        ]

        return [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": chunk,
                            },
                        }
                    ],
                },
            }
            for chunk in chunks
        ]

    async def get(
        self,
        resource_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        credentials = self._get_credentials(
            user_id
        )

        headers = self._headers(credentials)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/pages/{resource_id}",
                headers=headers,
            )

            if response.is_error:
                raise RuntimeError(
                    f"Notion page retrieval failed: "
                    f"{response.status_code} "
                    f"{response.text}"
                )

            page = response.json()

            blocks_response = await client.get(
                f"{self.base_url}/blocks/{resource_id}/children",
                headers=headers,
            )

            if blocks_response.is_error:
                raise RuntimeError(
                    f"Notion block retrieval failed: "
                    f"{blocks_response.status_code} "
                    f"{blocks_response.text}"
                )

        blocks = blocks_response.json().get(
            "results",
            []
        )

        content = self._blocks_to_text(blocks)

        return {
            "id": page.get("id"),
            "url": page.get("url"),
            "title": self._extract_title(page),
            "content": content,
        }

    async def create(
        self,
        title: str,
        content: str,
        user_id: str,
    ) -> dict[str, Any]:
        credentials = self._get_credentials(user_id)

        headers = self._headers(credentials)

        saved_at = datetime.now().strftime(
            "%d %B %Y at %H:%M"
        )

        content_with_metadata = (
            "Source: DataMCP Conversation\n"
            f"Saved: {saved_at}\n\n"
            f"{content}"
        )

        payload = {
            "parent": {
                "type": "workspace",
                "workspace": True,
            },
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": title,
                            },
                        }
                    ]
                }
            },
            "children": self._content_to_blocks(
                content_with_metadata
            ),
        }
  
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/pages",
                json=payload,
                headers=headers,
            )

        if response.is_error:
            raise RuntimeError(
                f"Notion page creation failed: "
                f"{response.status_code} {response.text}"
            )

        page = response.json()

        return {
            "id": page.get("id"),
            "object": page.get("object"),
            "url": page.get("url"),
            "title": self._extract_title(page),
        }

    async def update(
        self,
        resource_id: str,
        title: str,
        content: str,
        user_id: str,
    ) -> dict[str, Any]:
        credentials = self._get_credentials(user_id)

        headers = self._headers(credentials)

        properties_payload = {
            "title": {
                "title": [
                    {
                        "type": "text",
                        "text": {
                            "content": title,
                        },
                    }
                ]
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/pages/{resource_id}",
                json={
                    "properties": properties_payload,
                },
                headers=headers,
            )

            if response.is_error:
                raise RuntimeError(
                    f"Notion page update failed: "
                    f"{response.status_code} {response.text}"
                )

            page = response.json()

            blocks_response = await client.get(
                f"{self.base_url}/blocks/{resource_id}/children",
                headers=headers,
            )

            if blocks_response.is_error:
                raise RuntimeError(
                    f"Notion block retrieval failed: "
                    f"{blocks_response.status_code} "
                    f"{blocks_response.text}"
                )

            existing_blocks = blocks_response.json().get(
                "results",
                []
            )

            for block in existing_blocks:
                block_id = block.get("id")

                if block_id:
                    delete_response = await client.delete(
                        f"{self.base_url}/blocks/{block_id}",
                        headers=headers,
                    )

                    if delete_response.is_error:
                        raise RuntimeError(
                            f"Notion block deletion failed: "
                            f"{delete_response.status_code} "
                            f"{delete_response.text}"
                        )

            if content:
                blocks_payload = {
                    "children": self._content_to_blocks(
                        content
                    ),
                }

                blocks_response = await client.patch(
                    f"{self.base_url}/blocks/{resource_id}/children",
                    json=blocks_payload,
                    headers=headers,
                )

                if blocks_response.is_error:
                    raise RuntimeError(
                        f"Notion block creation failed: "
                        f"{blocks_response.status_code} "
                        f"{blocks_response.text}"
                    )

        return {
            "id": page.get("id"),
            "object": page.get("object"),
            "url": page.get("url"),
            "title": self._extract_title(page),
        }

notion_provider = NotionProvider()