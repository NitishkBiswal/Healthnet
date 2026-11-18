from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MatchResult(BaseModel):
    patient_id: UUID
    health_id: str
    confidence: float = Field(ge=0, le=1)
    band: str = Field(pattern="^(HIGH|MEDIUM)$")
    method: str = Field(pattern="^(DETERMINISTIC|PROBABILISTIC|BATCH_PROBABILISTIC)$")


class MergeRequest(BaseModel):
    source_patient_id: UUID
    target_patient_id: UUID
    reviewer_note: str | None = None


class MatchConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_key: str
    name_weight: float
    date_of_birth_weight: float
    sex_weight: float
    phone_weight: float
    email_weight: float
    medium_confidence: float
    high_confidence: float


class MatchConfigurationUpdate(BaseModel):
    name_weight: float = Field(ge=0, le=1)
    date_of_birth_weight: float = Field(ge=0, le=1)
    sex_weight: float = Field(ge=0, le=1)
    phone_weight: float = Field(ge=0, le=1)
    email_weight: float = Field(ge=0, le=1)
    medium_confidence: float = Field(ge=0, le=1)
    high_confidence: float = Field(ge=0, le=1)
