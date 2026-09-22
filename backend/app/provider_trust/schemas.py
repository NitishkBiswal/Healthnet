from pydantic import BaseModel
from enum import Enum

class TrustStatus(Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    # TODO: Implement in Segment 4

class OrganizationCreate(BaseModel):
    # TODO: Implement in Segment 4
    pass

class ProviderCreate(BaseModel):
    # TODO: Implement in Segment 4
    pass
