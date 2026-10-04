from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class TrustStatus(StrEnum):
    ACTIVE="ACTIVE"; SUSPENDED="SUSPENDED"; REVOKED="REVOKED"

class OrganizationCreate(BaseModel):
    external_id:str=Field(min_length=2,max_length=128)
    name:str=Field(min_length=2,max_length=200)
    jurisdiction:str=Field(min_length=2,max_length=32)
    issuer:str|None=None

class OrganizationResponse(OrganizationCreate):
    model_config=ConfigDict(from_attributes=True)
    id:UUID; trust_status:TrustStatus

class ProviderCreate(BaseModel):
    external_id:str=Field(min_length=2,max_length=128)
    given_name:str=Field(min_length=1,max_length=100)
    family_name:str=Field(min_length=1,max_length=100)
    license_number:str=Field(min_length=2,max_length=128)
    jurisdiction:str=Field(min_length=2,max_length=32)
    keycloak_subject:str|None=None

class ProviderResponse(ProviderCreate):
    model_config=ConfigDict(from_attributes=True)
    id:UUID; trust_status:TrustStatus

class PractitionerRoleCreate(BaseModel):
    provider_id:UUID
    organization_id:UUID
    role:str=Field(min_length=2,max_length=32)

class PractitionerRoleResponse(PractitionerRoleCreate):
    model_config=ConfigDict(from_attributes=True)
    id:UUID; active:bool
