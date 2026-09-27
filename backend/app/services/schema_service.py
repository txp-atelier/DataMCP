from app.models.schema import DatabaseSchema
from app.services.connection_manager import connection_manager


DEFAULT_USER_ID = "demo-user"


class SchemaService:

    def get_schema(
        self,
        connection_id: str,
        user_id: str = DEFAULT_USER_ID,
    ) -> DatabaseSchema:

        connection = connection_manager.get(
            connection_id,
            user_id,
        )

        if not connection:
            raise ValueError(
                f"Connection '{connection_id}' not found"
            )

        adapter = connection_manager.get_adapter(
            connection
        )

        try:
            schema = adapter.get_schema()

            return DatabaseSchema(
                tables=schema
            )

        finally:
            adapter.close()


schema_service = SchemaService()
