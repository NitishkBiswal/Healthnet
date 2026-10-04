from uuid import UUID
from pydantic import BaseModel
class ProvenanceRecord(BaseModel):
    health_id:str;repository_id:UUID|None=None;resource_type:str;resource_id:str;source_system:str;actor_id:str;action:str;details:dict={}
class ProvenanceResponse(ProvenanceRecord):
    id:UUID
