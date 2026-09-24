from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PatientIdentifierInput(BaseModel):
    identifier_type: str = Field(min_length=1, max_length=64)
    identifier_value: str = Field(min_length=1, max_length=256)
    issuing_authority: str | None = Field(default=None, max_length=128)


class PatientRegistrationRequest(BaseModel):
    given_name: str = Field(min_length=1, max_length=100)
    family_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    sex: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = None
    issuing_jurisdiction: str = Field(min_length=1, max_length=32)
    identifiers: list[PatientIdentifierInput] = Field(default_factory=list)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_health_id: str
    issuing_jurisdiction: str
    given_name: str
    family_name: str
    date_of_birth: date
    sex: str | None
    phone: str | None
    email: str | None
    address: str | None
    status: str
    superseded_by: UUID | None
    created_at: datetime


class HealthIdResponse(BaseModel):
    health_id: str
    internal_id: UUID
    issuing_jurisdiction: str
    status: str


class MatchCandidate(BaseModel):
    patient_id: UUID
    health_id: str
    confidence: float
    band: str


class RegistrationResult(BaseModel):
    outcome: str
    patient: PatientResponse | None = None
    matches: list[MatchCandidate] = Field(default_factory=list)
    duplicate_review_id: UUID | None = None


class DuplicateReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_patient_id: UUID
    confidence: float
    status: str
    reviewer_note: str | None
    created_at: datetime
    reviewed_at: datetime | None


class DuplicateReviewDecision(BaseModel):
    decision: str = Field(pattern="^(APPROVED_DUPLICATE|REJECTED)$")
    reviewer_note: str | None = None


class IdentityMergeRequest(BaseModel):
    source_patient_id: UUID
    target_patient_id: UUID
    reviewer_note: str | None = None


class LocationHistoryRequest(BaseModel):
    jurisdiction: str = Field(min_length=1, max_length=32)
    movement_type: str = Field(
        pattern="^(ORDINARY_TRAVEL|TEMPORARY_RELOCATION|CARE_EPISODE_ABROAD|PERMANENT_MIGRATION)$"
    )
    started_at: datetime
    ended_at: datetime | None = None
