from datetime import datetime
from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ConsentStatus(StrEnum):
    ACTIVE="ACTIVE"; REVOKED="REVOKED"; EXPIRED="EXPIRED"

class ConsentCreateRequest(BaseModel):
    health_id:str=Field(min_length=4,max_length=32)
    grantee_type:str=Field(min_length=2,max_length=32)
    grantee_id:str=Field(min_length=1,max_length=128)
    purpose:str=Field(min_length=2,max_length=128)
    scopes:list[str]=Field(min_length=1)
    valid_from:datetime
    valid_until:datetime|None=None
    reason:str|None=None

class ConsentResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:UUID; health_id:str; grantee_type:str; grantee_id:str; purpose:str; scopes:list[str]
    status:ConsentStatus; valid_from:datetime; valid_until:datetime|None=None; revoked_at:datetime|None=None; reason:str|None=None

class ConsentCheckRequest(BaseModel):
    health_id:str; grantee_id:str; purpose:str; scope:str; at:datetime|None=None


class AuthorizedPatientResponse(BaseModel):
    health_id: str
    given_name: str
    family_name: str
    consent_id: UUID
    purpose: str
    scopes: list[str]
    valid_from: datetime
    valid_until: datetime | None = None
