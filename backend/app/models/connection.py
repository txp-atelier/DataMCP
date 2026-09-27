from enum import Enum

from pydantic import BaseModel, Field


class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class DatabaseConnection(BaseModel):
    id: str
    user_id: str
    name: str
    database_type: DatabaseType
    connection_string: str
    status: str = "unknown"


class CreateConnectionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    database_type: DatabaseType
    connection_string: str = Field(min_length=1)


class DatabaseConnectionResponse(BaseModel):
    id: str
    name: str
    database_type: DatabaseType
    status: str = "unknown"


class UpdateConnectionRequest(BaseModel):
    name: str = Field(min_length=1)
    database_type: DatabaseType
    connection_string: str = ""