from uuid import UUID
from pydantic import BaseModel, Field

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
    jurisdiction_code:str
    name:str
    purpose:str
    scope:str
    effect:str="ALLOW"
    description:str|None=None
