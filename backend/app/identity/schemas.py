import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


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
    # Format-only check. HealthNet does not call UIDAI or claim Aadhaar verification.
    aadhaar_number: SecretStr | None = None
    identifiers: list[PatientIdentifierInput] = Field(default_factory=list)

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar_number(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not re.fullmatch(r"\d{12}", value.get_secret_value()):
            raise ValueError("Aadhaar number must contain exactly 12 digits")
        return value

    @model_validator(mode="after")
    def prevent_plaintext_aadhaar_identifier(self) -> "PatientRegistrationRequest":
        if any(
            any(token in item.identifier_type.strip().upper() for token in ("AADHAAR", "AADHAR", "UIDAI"))
            or item.identifier_type.strip().upper() == "UID"
            for item in self.identifiers
        ):
            raise ValueError(
                "Use the dedicated aadhaar_number field; Aadhaar must not be stored as a plaintext identifier"
            )
        return self


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
    candidate_health_id: str | None = None
    target_health_id: str | None = None
    review_type: str = "DUPLICATE_REGISTRATION"
    target_patient_id: UUID | None = None
    proposed_address: str | None = None
    confidence: float
    status: str
    reviewer_note: str | None
    proposed_given_name: str
    proposed_family_name: str
    proposed_date_of_birth: date
    proposed_sex: str | None
    proposed_phone: str | None
    proposed_email: str | None
    proposed_issuing_jurisdiction: str | None
    proposed_identifiers: list[dict[str, str | None]] | None
    created_at: datetime
    reviewed_at: datetime | None


class DuplicateReviewDecision(BaseModel):
    decision: str = Field(pattern="^(APPROVED_DUPLICATE|APPROVED_PROFILE_UPDATE|REJECTED)$")
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


class PatientProfileUpdate(BaseModel):
    given_name: str = Field(min_length=1, max_length=100)
    family_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    sex: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = None


class ProfileUpdateResult(BaseModel):
    outcome: str
    patient: PatientResponse | None = None
    duplicate_review_id: UUID | None = None


class AadhaarUpdateRequest(BaseModel):
    aadhaar_number: SecretStr

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar_number(cls, value: SecretStr) -> SecretStr:
        if not re.fullmatch(r"\d{12}", value.get_secret_value()):
            raise ValueError("Aadhaar number must contain exactly 12 digits")
        return value


class AadhaarStatusResponse(BaseModel):
    has_aadhaar: bool
    masked_value: str | None = None
