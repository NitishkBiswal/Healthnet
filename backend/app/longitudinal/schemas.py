from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataCompleteness(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class LongitudinalViewRequest(BaseModel):
    health_id: str
    purpose: str
    scope: str


class LongitudinalViewResponse(BaseModel):
    health_id: str
    current_repository: dict[str, Any] | None = None
    completeness: DataCompleteness
    records: list[dict[str, Any]] = Field(default_factory=list)
    repositories_checked: int
    repositories_available: int
    errors: list[str] = Field(default_factory=list)
