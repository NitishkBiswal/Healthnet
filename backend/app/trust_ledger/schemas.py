from datetime import datetime
from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

FORBIDDEN_FIELDS = {"patient_name","diagnosis","prescription","image","lab_result","clinical_note","aadhaar","passport","ssn","cleartext_health_id","fhir_clinical_content","phi","pii"}

class LedgerEventType(StrEnum):
    ACCESS_GRANTED = "ACCESS_GRANTED"
    TRANSFER_AUTHORIZED = "TRANSFER_AUTHORIZED"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"
    CONSENT_RECORDED = "CONSENT_RECORDED"

class LedgerEntryCreate(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    event_type: LedgerEventType
    opaque_subject_reference: str = Field(min_length=1, max_length=256)
    source_repository_id: UUID | None = None
    destination_repository_id: UUID | None = None
    authorization_reference: str = Field(min_length=1, max_length=256)
    package_hash: str = Field(min_length=16, max_length=128)
    status: str = Field(min_length=1, max_length=32)
    audit_reference: str | None = Field(default=None, max_length=256)

class LedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    transaction_id: str
    event_type: LedgerEventType
    opaque_subject_reference: str
    source_repository_id: UUID | None
    destination_repository_id: UUID | None
    authorization_reference: str
    package_hash: str
    timestamp: datetime
    status: str
    audit_reference: str | None
    previous_entry_hash: str | None
    entry_hash: str
