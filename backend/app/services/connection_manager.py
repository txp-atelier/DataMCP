import json
import os
from pathlib import Path
from typing import Dict

from cryptography.fernet import Fernet, InvalidToken

from app.models.connection import (
    DatabaseConnection,
    DatabaseType,
)
from app.adapters.base import DatabaseAdapter
from app.adapters.postgres import PostgreSQLAdapter
from app.adapters.mysql import MySQLAdapter
from app.adapters.mongodb import MongoDBAdapter


DEFAULT_USER_ID = "demo-user"


class ConnectionManager:

    def __init__(self):
        self._connections: Dict[str, DatabaseConnection] = {}
        self._secrets: Dict[str, str] = {}
        self._secrets_migrated = False
        self._connections_migrated = False

        self._data_path = (
            Path(__file__).resolve().parent.parent
            / "data"
        )

        self._connections_path = (
            self._data_path / "connections.json"
        )

        self._secrets_path = (
            self._data_path / "connection_secrets.json"
        )

        self._secret_key = os.getenv(
            "DATAMCP_SECRET_KEY"
        )

        if not self._secret_key:
            raise RuntimeError(
                "DATAMCP_SECRET_KEY is not configured"
            )

        try:
            self._fernet = Fernet(
                self._secret_key.encode()
            )
        except Exception as error:
            raise RuntimeError(
                "DATAMCP_SECRET_KEY is invalid"
            ) from error

        self._data_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._load()

    def _encrypt(self, value: str) -> str:
        return self._fernet.encrypt(
            value.encode()
        ).decode()

    def _decrypt(self, value: str) -> str:
        return self._fernet.decrypt(
            value.encode()
        ).decode()

    def _load(self) -> None:
        self._load_secrets()
        self._load_connections()

        if (
            self._secrets_migrated
            or self._connections_migrated
        ):
            self._save()

    def _load_secrets(self) -> None:
        if not self._secrets_path.exists():
            return

        try:
            with open(
                self._secrets_path,
                "r",
                encoding="utf-8",
            ) as file:
                stored_secrets = json.load(file)

            if not isinstance(
                stored_secrets,
                dict,
            ):
                return

            for connection_id, stored_value in (
                stored_secrets.items()
            ):
                try:
                    self._secrets[
                        connection_id
                    ] = self._decrypt(
                        stored_value
                    )

                except InvalidToken:
                    self._secrets[
                        connection_id
                    ] = stored_value

                    self._secrets_migrated = True

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            self._secrets = {}

    def _load_connections(self) -> None:
        if not self._connections_path.exists():
            return

        try:
            with open(
                self._connections_path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            for item in data:
                connection_id = item["id"]

                connection_string = self._secrets.get(
                    connection_id
                )

                if connection_string is None:
                    continue

                user_id = item.get(
                    "user_id",
                    DEFAULT_USER_ID,
                )

                if "user_id" not in item:
                    self._connections_migrated = True

                connection = DatabaseConnection(
                    id=connection_id,
                    user_id=user_id,
                    name=item["name"],
                    database_type=item["database_type"],
                    connection_string=connection_string,
                    status=item.get(
                        "status",
                        "unknown",
                    ),
                )

                self._connections[
                    connection.id
                ] = connection

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
            KeyError,
        ):
            self._connections = {}

    def _save(self) -> None:
        connection_data = []

        for connection in self._connections.values():
            connection_data.append(
                {
                    "id": connection.id,
                    "user_id": connection.user_id,
                    "name": connection.name,
                    "database_type": (
                        connection.database_type.value
                    ),
                    "status": connection.status,
                }
            )

        with open(
            self._connections_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                connection_data,
                file,
                indent=2,
            )

        encrypted_secrets = {
            connection_id: self._encrypt(
                connection_string
            )
            for connection_id, connection_string
            in self._secrets.items()
        }

        with open(
            self._secrets_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                encrypted_secrets,
                file,
                indent=2,
            )

    def add(
        self,
        connection: DatabaseConnection,
    ) -> DatabaseConnection:

        self._connections[
            connection.id
        ] = connection

        self._secrets[
            connection.id
        ] = connection.connection_string

        self._save()

        return connection

    def get(
        self,
        connection_id: str,
        user_id: str,
    ) -> DatabaseConnection | None:

        connection = self._connections.get(
            connection_id
        )

        if connection is None:
            return None

        if connection.user_id != user_id:
            return None

        return connection

    def get_all(
        self,
        user_id: str,
    ) -> list[DatabaseConnection]:

        return [
            connection
            for connection in self._connections.values()
            if connection.user_id == user_id
        ]

    def update(
        self,
        connection: DatabaseConnection,
        user_id: str,
    ) -> DatabaseConnection:

        existing = self._connections.get(
            connection.id
        )

        if existing is None:
            raise ValueError(
                "Connection not found"
            )

        if existing.user_id != user_id:
            raise ValueError(
                "Connection not found"
            )

        if connection.user_id != user_id:
            raise ValueError(
                "Connection does not belong to user"
            )

        self._connections[
            connection.id
        ] = connection

        self._secrets[
            connection.id
        ] = connection.connection_string

        self._save()

        return connection

    def delete(
        self,
        connection_id: str,
        user_id: str,
    ) -> bool:

        connection = self._connections.get(
            connection_id
        )

        if connection is None:
            return False

        if connection.user_id != user_id:
            return False

        del self._connections[
            connection_id
        ]

        self._secrets.pop(
            connection_id,
            None,
        )

        self._save()

        return True

    def get_adapter(
        self,
        connection: DatabaseConnection,
    ) -> DatabaseAdapter:

        if (
            connection.database_type
            == DatabaseType.POSTGRESQL
        ):
            return PostgreSQLAdapter(
                connection.connection_string
            )

        if (
            connection.database_type
            == DatabaseType.MYSQL
        ):
            return MySQLAdapter(
                connection.connection_string
            )

        if (
            connection.database_type
            == DatabaseType.MONGODB
        ):
            return MongoDBAdapter(
                connection.connection_string
            )

        raise ValueError(
            f"Unsupported database type: "
            f"{connection.database_type}"
        )


connection_manager = ConnectionManager()
