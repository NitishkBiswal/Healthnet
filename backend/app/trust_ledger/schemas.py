from pydantic import BaseModel
from enum import Enum
from typing import List

FORBIDDEN_FIELDS: List[str] = [
    "patient_name", "diagnosis", "prescription", "image", "lab_result",
    "clinical_note", "aadhaar", "passport", "ssn", "cleartext_health_id",
    "fhir_clinical_content", "phi", "pii"
]

class LedgerEventType(Enum):
    ACCESS_GRANTED = "ACCESS_GRANTED"
    TRANSFER_AUTHORIZED = "TRANSFER_AUTHORIZED"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"
    CONSENT_RECORDED = "CONSENT_RECORDED"

class LedgerEntryCreate(BaseModel):
    # TODO: Implement in Segment 11
    pass

class LedgerEntryResponse(BaseModel):
    # TODO: Implement in Segment 11
    pass
