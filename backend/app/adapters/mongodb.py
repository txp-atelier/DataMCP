from pymongo import MongoClient

from app.adapters.base import DatabaseAdapter


class MongoDBAdapter(DatabaseAdapter):
    def __init__(self, connection_string: str):
        super().__init__(connection_string)
        self.client = MongoClient(connection_string)

    def test_connection(self) -> bool:
        try:
            self.client.admin.command("ping")
            return True

        except Exception:
            return False

    def get_schema(self) -> dict:
        database = self.client.get_default_database()
        schema = {}

        for collection_name in database.list_collection_names():
            sample_document = database[collection_name].find_one()

            if sample_document:
                columns = []

                for field_name, field_value in sample_document.items():
                    columns.append(
                        {
                            "name": field_name,
                            "type": type(field_value).__name__,
                            "nullable": field_value is None,
                            "primary_key": field_name == "_id",
                            "foreign_key": None,
                        }
                    )

                schema[collection_name] = {
                    "columns": columns
                }

            else:
                schema[collection_name] = {
                    "columns": []
                }

        return schema

    def get_sample_data(
        self,
        collection_name: str,
        limit: int = 5,
    ) -> list[dict]:

        database = self.client.get_default_database()

        if collection_name not in database.list_collection_names():
            raise ValueError(
                f"Collection '{collection_name}' not found"
            )

        if limit < 1 or limit > 100:
            raise ValueError(
                "Limit must be between 1 and 100"
            )

        documents = database[collection_name].find().limit(limit)

        result = []

        for document in documents:
            document["_id"] = str(document["_id"])
            result.append(document)

        return result

    def execute_mongodb_query(
        self,
        collection_name: str,
        filter_query: dict | None = None,
        projection: dict | None = None,
        limit: int = 100,
    ) -> list[dict]:

        database = self.client.get_default_database()

        if collection_name not in database.list_collection_names():
            raise ValueError(
                f"Collection '{collection_name}' not found"
            )

        if limit < 1 or limit > 100:
            raise ValueError(
                "Limit must be between 1 and 100"
            )

        documents = database[collection_name].find(
            filter_query or {},
            projection,
        ).limit(limit)

        result = []

        for document in documents:
            document["_id"] = str(document["_id"])
            result.append(document)

        return result

    def close(self) -> None:
        self.client.close()