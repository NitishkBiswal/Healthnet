from enum import StrEnum
from pydantic import BaseModel,Field
class RetrievalTier(StrEnum): TIER_1="TIER_1";TIER_2="TIER_2";TIER_3="TIER_3";TIER_4="TIER_4"
class EmergencyProfileResponse(BaseModel):
    health_id:str;blood_group:str|None=None;allergies:list[str];medications:list[str];conditions:list[str];emergency_contacts:list[str]
class BreakGlassRequest(BaseModel):
    actor_id:str|None=None;reason:str=Field(min_length=5,max_length=1000);tier:RetrievalTier=RetrievalTier.TIER_1


class BreakGlassSummaryResponse(BaseModel):
    """Minimal chronic-condition summary returned after a one-time break-glass read."""
    health_id: str
    chronic_conditions: list[str]
    access_expires_at: str
