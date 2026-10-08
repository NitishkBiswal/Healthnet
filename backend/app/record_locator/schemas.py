from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RecordLocationEntry(BaseModel):
    repository_id: UUID
    endpoint: str | None = None
    resource_types: list[str] = Field(min_length=1)
    status: str = "ACTIVE"
    notes: str | None = None


class RecordLocationResponse(BaseModel):
    id: UUID
    health_id: str
    repository_id: UUID
    endpoint: str
    resource_types: list[str]
    status: str
    last_verified_at: datetime | None = None
    notes: str | None = None


class CurrentRecordLocationResponse(BaseModel):
    health_id: str
    repository_id: UUID
    repository_code: str
    repository_name: str
    jurisdiction: str
    endpoint: str
    resource_types: list[str]
    assigned_at: datetime | None = None
