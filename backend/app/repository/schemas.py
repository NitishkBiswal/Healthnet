from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RepositoryStatus(StrEnum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"


class RepositoryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    jurisdiction: str = Field(min_length=2, max_length=32)
    base_url: str = Field(min_length=1, max_length=512)
    description: str | None = None


class RepositoryInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    jurisdiction: str
    base_url: str
    status: RepositoryStatus
    description: str | None = None
    last_checked_at: datetime | None = None


class CustodyCreate(BaseModel):
    health_id: str = Field(min_length=4, max_length=32)
    repository_id: UUID
    resource_types: list[str] = Field(min_length=1)
    custody_start: datetime
    custody_end: datetime | None = None


class CustodyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    health_id: str
    repository_id: UUID
    resource_types: list[str]
    custody_start: datetime
    custody_end: datetime | None = None
