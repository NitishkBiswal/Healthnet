from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class FHIRResource(BaseModel):
    resourceType: str
    id: Optional[str] = None
    # TODO: Implement in Segment 7

class FHIRBundle(BaseModel):
    type: str
    total: Optional[int] = None
    entry: List[Dict[str, Any]] = []
    # TODO: Implement in Segment 7

class FHIRCapabilityStatement(BaseModel):
    # TODO: Implement in Segment 7
    pass
