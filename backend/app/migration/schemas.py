from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MigrationState(StrEnum):
    REQUESTED = "REQUESTED"
    PATIENT_AUTHORIZED = "PATIENT_AUTHORIZED"
    POLICY_LEGAL_CHECK = "POLICY_LEGAL_CHECK"
    TRANSFER_AUTH_ISSUED = "TRANSFER_AUTH_ISSUED"
    FHIR_EXPORT = "FHIR_EXPORT"
    VALIDATION = "VALIDATION"
    HASH_GENERATION = "HASH_GENERATION"
    ENCRYPTED_TRANSFER = "ENCRYPTED_TRANSFER"
    DESTINATION_VALIDATION = "DESTINATION_VALIDATION"
    HASH_VERIFICATION = "HASH_VERIFICATION"
    IMPORT_COMPLETED = "IMPORT_COMPLETED"
    SOURCE_ARCHIVED_READONLY = "SOURCE_ARCHIVED_READONLY"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TransferRequestCreate(BaseModel):
    health_id: str = Field(min_length=4, max_length=32)
    source_repository_id: UUID
    destination_repository_id: UUID
    purpose: str = Field(min_length=2, max_length=128)
    scope: str = Field(min_length=1, max_length=128)


class TransferAuthorizationRequest(BaseModel):
    authorization_reference: str = Field(min_length=1, max_length=256)


class TransferExecuteRequest(BaseModel):
    resource_count: int = Field(default=0, ge=0, le=1000000)
    package_hash: str = Field(min_length=16, max_length=128)


class TransferStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    health_id: str
    source_repository_id: UUID
    destination_repository_id: UUID
    purpose: str
    scope: str
    state: MigrationState
    authorization_reference: str | None
    package_hash: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class TransferManifestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transfer_request_id: UUID
    resource_count: int
    manifest_hash: str
    package_hash: str
    validation_status: str
    created_at: datetime
