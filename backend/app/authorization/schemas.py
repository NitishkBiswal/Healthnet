from pydantic import BaseModel, Field

class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str

class AuthorizationRequest(BaseModel):
    health_id: str = Field(min_length=4, max_length=32)
    grantee_id: str = Field(min_length=1, max_length=128)
    purpose: str = Field(min_length=2, max_length=128)
    scope: str = Field(min_length=1, max_length=128)
    organization_id: str | None = None
