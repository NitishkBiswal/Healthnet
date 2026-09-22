from pydantic import BaseModel
from enum import Enum

class RepositoryStatus(Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    # TODO: Implement in Segment 2

class RepositoryInfo(BaseModel):
    # TODO: Implement in Segment 2
    pass
