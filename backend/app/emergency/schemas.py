from pydantic import BaseModel
from enum import Enum

class RetrievalTier(Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    TIER_4 = "TIER_4"

class EmergencyProfileResponse(BaseModel):
    # TODO: Implement in Segment 9
    pass

class BreakGlassRequest(BaseModel):
    # TODO: Implement in Segment 9
    pass
