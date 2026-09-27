from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class IntegrationProvider(str, Enum):
    NOTION = "notion"
    GOOGLE_DOCS = "google_docs"


class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class IntegrationConnection(BaseModel):
    id: str
    user_id: str
    provider: IntegrationProvider
    status: IntegrationStatus
    external_account_id: str | None = None
    scopes: list[str] = []
    created_at: datetime
    updated_at: datetime


class CreateIntegrationConnection(BaseModel):
    provider: IntegrationProvider


class NotionPageRequest(BaseModel):
    title: str
    content: str