from enum import Enum
from typing import Protocol

class Role(str, Enum):
    PATIENT = "PATIENT"
    PROVIDER = "PROVIDER"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    SYSTEM = "SYSTEM"

class RBACService(Protocol):
    async def check_role(self, role: Role) -> bool:
        """Check if current user has the specified role."""
        ...

# TODO: Implement in Segment 4
