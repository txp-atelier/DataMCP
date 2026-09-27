from pydantic import BaseModel


class ForeignKeyInfo(BaseModel):
    table: str
    column: str | None = None


class ColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool
    primary_key: bool
    foreign_key: ForeignKeyInfo | None = None


class TableSchema(BaseModel):
    columns: list[ColumnSchema]


class DatabaseSchema(BaseModel):
    tables: dict[str, TableSchema]