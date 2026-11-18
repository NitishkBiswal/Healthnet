from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceRecord(BaseModel):
    health_id: str = Field(min_length=4, max_length=32)
    repository_id: UUID | None = None
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: str = Field(min_length=1, max_length=128)
    source_system: str = Field(min_length=1, max_length=256)
    actor_id: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=64)
    details: dict[str, Any] = Field(default_factory=dict)


class ProvenanceCreateRequest(BaseModel):
    health_id: str = Field(min_length=4, max_length=32)
    repository_id: UUID | None = None
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: str = Field(min_length=1, max_length=128)
    source_system: str = Field(min_length=1, max_length=256)
    action: str = Field(min_length=1, max_length=64)
    details: dict[str, Any] = Field(default_factory=dict)


class ProvenanceResponse(ProvenanceRecord):
    id: UUID
    recorded_at: datetime


class FHIRProvenanceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resourceType: Literal["Provenance"] = "Provenance"
    id: str
    target: list[dict[str, Any]]
    recorded: datetime
    agent: list[dict[str, Any]]
    activity: dict[str, Any]
    entity: list[dict[str, Any]]
