from pydantic import BaseModel
from enum import Enum

class AuditEventType(Enum):
    ACCESS = "ACCESS"
    RETRIEVAL = "RETRIEVAL"
    TRANSFER = "TRANSFER"
    MIGRATION = "MIGRATION"
    CONSENT_GRANT = "CONSENT_GRANT"
    CONSENT_REVOKE = "CONSENT_REVOKE"
    BREAK_GLASS = "BREAK_GLASS"
    POLICY_DECISION = "POLICY_DECISION"
    IDENTITY_MERGE = "IDENTITY_MERGE"
    REGISTRATION = "REGISTRATION"

class AuditEventResponse(BaseModel):
    # TODO: Implement in Segment 10
    pass
