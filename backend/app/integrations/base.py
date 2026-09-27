from abc import ABC, abstractmethod
from typing import Any


class KnowledgeProvider(ABC):
    """
    Generic interface for external knowledge providers
    such as Notion, Google Docs, etc.
    """

    provider_name: str

    @abstractmethod
    async def search(
        self,
        query: str,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """
        Search knowledge available to the user.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        resource_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve a specific knowledge resource.
        """
        raise NotImplementedError

    @abstractmethod
    async def create(
        self,
        title: str,
        content: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Create a new knowledge resource.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        resource_id: str,
        title: str,
        content: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Update an existing knowledge resource.
        """
        raise NotImplementedError