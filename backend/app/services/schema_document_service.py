from app.models.schema import DatabaseSchema
from app.services.rag_service import rag_service


DEFAULT_USER_ID = "demo-user"


class SchemaDocumentService:

    def create_documents(
        self,
        schema: DatabaseSchema,
        connection_id: str,
        user_id: str = DEFAULT_USER_ID,
    ) -> list[dict]:

        documents = []

        for table_name, table in schema.tables.items():

            columns = []

            for column in table.columns:
                column_description = (
                    f"{column.name} "
                    f"({column.type})"
                )

                if column.primary_key:
                    column_description += " PRIMARY KEY"

                if column.foreign_key:
                    column_description += (
                        f" FOREIGN KEY REFERENCES "
                        f"{column.foreign_key.table}"
                        f"({column.foreign_key.column})"
                    )

                if not column.nullable:
                    column_description += " NOT NULL"

                columns.append(
                    column_description
                )

            document = {
                "user_id": user_id,
                "connection_id": connection_id,
                "table": table_name,
                "content": (
                    f"Database connection: {connection_id}\n"
                    f"Table: {table_name}\n"
                    f"Columns:\n"
                    + "\n".join(
                        f"- {column}"
                        for column in columns
                    )
                ),
            }

            documents.append(document)

        return documents

    def ingest_documents(
        self,
        documents: list[dict],
    ) -> dict:

        return rag_service.ingest_documents(
            documents
        )


schema_document_service = SchemaDocumentService()
