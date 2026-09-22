from typing import Protocol
from pydantic import BaseModel

class AccessContext(BaseModel):
    actor_id: str
    actor_role: str
    purpose: str
    jurisdiction: str
    resource_type: str
    emergency_flag: bool = False

class ABACService(Protocol):
    async def evaluate(self, context: AccessContext) -> bool:
        """Evaluate access context against policies."""
        ...

# TODO: Implement in Segment 5
