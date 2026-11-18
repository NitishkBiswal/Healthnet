from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class PolicyEvaluationRequest(BaseModel):
    source_jurisdiction:str=Field(min_length=2,max_length=32)
    destination_jurisdiction:str=Field(min_length=2,max_length=32)
    purpose:str=Field(min_length=2,max_length=128)
    scope:str=Field(min_length=1,max_length=128)

class PolicyEvaluationResult(BaseModel):
    allowed:bool
    reason:str
    matched_rule_id:UUID|None=None

class JurisdictionInfo(BaseModel):
    code:str
    name:str
    active:bool

class PolicyRuleCreate(BaseModel):
    jurisdiction_code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    purpose: str = Field(min_length=2, max_length=128)
    scope: str = Field(min_length=1, max_length=128)
    effect: Literal["ALLOW", "DENY"] = "ALLOW"
    description: str | None = None


class JurisdictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    active: bool


class PolicyRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    jurisdiction_id: UUID
    name: str
    purpose: str
    scope: str
    effect: str
    description: str | None
    active: bool
