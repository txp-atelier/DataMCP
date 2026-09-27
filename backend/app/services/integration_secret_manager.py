import json
import os

from cryptography.fernet import Fernet


class IntegrationSecretManager:
    def __init__(self):
        self.data_dir = "app/data"
        self.file_path = os.path.join(
            self.data_dir,
            "integration_secrets.json",
        )

        os.makedirs(self.data_dir, exist_ok=True)

        secret_key = os.getenv("DATAMCP_SECRET_KEY")

        if not secret_key:
            raise RuntimeError(
                "DATAMCP_SECRET_KEY is not configured"
            )

        self.fernet = Fernet(secret_key.encode())

        if not os.path.exists(self.file_path):
            self._save({})

    def _load(self) -> dict:
        with open(
            self.file_path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _save(self, secrets: dict):
        with open(
            self.file_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                secrets,
                file,
                indent=2,
            )

    def save(
        self,
        integration_id: str,
        credentials: dict,
    ):
        secrets = self._load()

        encrypted = self.fernet.encrypt(
            json.dumps(credentials).encode()
        ).decode()

        secrets[integration_id] = encrypted

        self._save(secrets)

    def get(
        self,
        integration_id: str,
    ) -> dict | None:
        secrets = self._load()

        encrypted = secrets.get(integration_id)

        if not encrypted:
            return None

        decrypted = self.fernet.decrypt(
            encrypted.encode()
        )

        return json.loads(decrypted.decode())

    def delete(
        self,
        integration_id: str,
    ):
        secrets = self._load()

        if integration_id in secrets:
            del secrets[integration_id]
            self._save(secrets)