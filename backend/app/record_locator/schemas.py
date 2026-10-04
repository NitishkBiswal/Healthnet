from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class RecordLocationEntry(BaseModel):
    repository_id: UUID
    endpoint: str = Field(min_length=1, max_length=512)
    resource_types: list[str] = Field(min_length=1)
    status: str = "ACTIVE"
    notes: str | None = None

class RecordLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    health_id: str
    repository_id: UUID
    endpoint: str
    resource_types: list[str]
    status: str
    last_verified_at: datetime | None = None
    notes: str | None = None
