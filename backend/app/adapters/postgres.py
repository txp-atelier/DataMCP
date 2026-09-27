from sqlalchemy import create_engine, inspect, text

from app.adapters.base import DatabaseAdapter


class PostgreSQLAdapter(DatabaseAdapter):
    def __init__(self, connection_string: str):
        super().__init__(connection_string)
        self.engine = create_engine(connection_string)

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            return True

        except Exception:
            return False

    def get_schema(self) -> dict:
        inspector = inspect(self.engine)

        schema = {}

        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            primary_key = inspector.get_pk_constraint(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)

            primary_key_columns = primary_key.get("constrained_columns", [])

            foreign_key_columns = {}

            for foreign_key in foreign_keys:
                constrained_columns = foreign_key.get(
                    "constrained_columns",
                    []
                )
                referred_table = foreign_key.get("referred_table")
                referred_columns = foreign_key.get(
                    "referred_columns",
                    []
                )

                for index, column_name in enumerate(constrained_columns):
                    foreign_key_columns[column_name] = {
                        "table": referred_table,
                        "column": (
                            referred_columns[index]
                            if index < len(referred_columns)
                            else None
                        ),
                    }

            schema[table_name] = {
                "columns": [
                    {
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": column["nullable"],
                        "primary_key": column["name"] in primary_key_columns,
                        "foreign_key": foreign_key_columns.get(
                            column["name"]
                        ),
                    }
                    for column in columns
                ]
            }

        return schema

    def get_sample_data(
        self,
        table_name: str,
        limit: int = 5
    ) -> list[dict]:
        inspector = inspect(self.engine)

        if table_name not in inspector.get_table_names():
            raise ValueError(f"Table '{table_name}' not found")

        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")

        query = text(
            f'SELECT * FROM "{table_name}" LIMIT :limit'
        )

        with self.engine.connect() as connection:
            result = connection.execute(
                query,
                {"limit": limit},
            )

            return [
                dict(row._mapping)
                for row in result
            ]

    def execute_read_query(
        self,
        query: str,
    ) -> list[dict]:
        with self.engine.connect() as connection:
            result = connection.execute(text(query))

            return [
                dict(row._mapping)
                for row in result
            ]

    def close(self) -> None:
        self.engine.dispose()