import json
import os
from datetime import datetime, timezone

from app.models.integration import (
    CreateIntegrationConnection,
    IntegrationConnection,
    IntegrationStatus,
)


class IntegrationManager:
    def __init__(self):
        self.data_dir = "app/data"
        self.file_path = os.path.join(
            self.data_dir,
            "integrations.json",
        )

        os.makedirs(self.data_dir, exist_ok=True)

        if not os.path.exists(self.file_path):
            self._save([])

    def _load(self) -> list[dict]:
        with open(self.file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _save(self, integrations: list[dict]):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(integrations, file, indent=2)

    def create(
        self,
        request: CreateIntegrationConnection,
        user_id: str,
    ) -> IntegrationConnection:
        integrations = self._load()

        # Return existing integration for this provider
        for item in integrations:
            if (
                item["user_id"] == user_id
                and item["provider"] == request.provider.value
            ):
                return IntegrationConnection(**item)

        now = datetime.now(timezone.utc)

        integration = IntegrationConnection(
            id=os.urandom(16).hex(),
            user_id=user_id,
            provider=request.provider,
            status=IntegrationStatus.DISCONNECTED,
            created_at=now,
            updated_at=now,
        )

        integrations.append(
            integration.model_dump(mode="json")
        )

        self._save(integrations)

        return integration

    def get_all(
        self,
        user_id: str,
    ) -> list[IntegrationConnection]:
        integrations = self._load()

        return [
            IntegrationConnection(**item)
            for item in integrations
            if item["user_id"] == user_id
        ]

    def get(
        self,
        integration_id: str,
        user_id: str,
    ) -> IntegrationConnection | None:
        integrations = self._load()

        for item in integrations:
            if (
                item["id"] == integration_id
                and item["user_id"] == user_id
            ):
                return IntegrationConnection(**item)

        return None

    def update(
        self,
        integration_id: str,
        user_id: str,
        status: IntegrationStatus | None = None,
        external_account_id: str | None = None,
        scopes: list[str] | None = None,
    ) -> IntegrationConnection | None:
        integrations = self._load()

        for item in integrations:
            if (
                item["id"] == integration_id
                and item["user_id"] == user_id
            ):
                if status is not None:
                    item["status"] = status.value

                if external_account_id is not None:
                    item["external_account_id"] = external_account_id

                if scopes is not None:
                    item["scopes"] = scopes

                item["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                self._save(integrations)

                return IntegrationConnection(**item)

        return None

    def disconnect(
        self,
        integration_id: str,
        user_id: str,
    ) -> IntegrationConnection | None:
        integrations = self._load()

        for item in integrations:
            if (
                item["id"] == integration_id
                and item["user_id"] == user_id
            ):
                item["status"] = IntegrationStatus.DISCONNECTED.value
                item["external_account_id"] = None
                item["scopes"] = []
                item["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                self._save(integrations)

                return IntegrationConnection(**item)

        return None