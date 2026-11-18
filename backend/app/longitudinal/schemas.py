from enum import Enum
from typing import Any
from datetime import date

from pydantic import BaseModel, Field, model_validator

class DataCompleteness(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"

class LongitudinalViewRequest(BaseModel):
    health_id: str
    purpose: str
    scope: str
    from_date: date | None = None
    to_date: date | None = None
    resource_types: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_date_range(self) -> "LongitudinalViewRequest":
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("from_date must be on or before to_date")
        if any(not value or len(value) > 64 for value in self.resource_types):
            raise ValueError("resource_types must contain valid FHIR resource types")
        return self

class LongitudinalViewResponse(BaseModel):
    health_id: str
    completeness: DataCompleteness
    records: list[dict[str, Any]] = Field(default_factory=list)
    repositories_checked: int
    repositories_available: int
    errors: list[str] = Field(default_factory=list)
