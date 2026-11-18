from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RetrievalTier(StrEnum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    TIER_4 = "TIER_4"


class EmergencyProfileRequest(BaseModel):
    blood_group: str | None = Field(default=None, max_length=8)
    allergies: list[str] = Field(default_factory=list, max_length=100)
    medications: list[str] = Field(default_factory=list, max_length=100)
    conditions: list[str] = Field(default_factory=list, max_length=100)
    emergency_contacts: list[str] = Field(default_factory=list, max_length=20)


class EmergencyProfileResponse(EmergencyProfileRequest):
    health_id: str
    updated_at: datetime | None = None


class BreakGlassRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)
    tier: RetrievalTier = RetrievalTier.TIER_1


class BreakGlassResponse(BaseModel):
    event_id: UUID
    health_id: str
    authorization_token: str
    expires_at: datetime


class PatientNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    health_id: str
    event_type: str
    message: str
    created_at: datetime
    read_at: datetime | None
