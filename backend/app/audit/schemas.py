from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel,Field
class AuditEventType(StrEnum):
    ACCESS="ACCESS";RETRIEVAL="RETRIEVAL";RECORD_CREATE="RECORD_CREATE";RECORD_UPDATE="RECORD_UPDATE";RECORD_DELETE="RECORD_DELETE";RECORD_ARCHIVE="RECORD_ARCHIVE";TRANSFER="TRANSFER";MIGRATION="MIGRATION";CONSENT_GRANT="CONSENT_GRANT";CONSENT_REVOKE="CONSENT_REVOKE";BREAK_GLASS="BREAK_GLASS";POLICY_DECISION="POLICY_DECISION";IDENTITY_MERGE="IDENTITY_MERGE";REGISTRATION="REGISTRATION";REPOSITORY_CHANGE="REPOSITORY_CHANGE"
class AuditEventCreate(BaseModel):
    event_type:AuditEventType;health_id:str|None=None;actor_id:str=Field(min_length=1,max_length=128);action:str;payload:dict={}
class AuditEventResponse(BaseModel):
    id:UUID;event_type:AuditEventType;health_id:str|None;actor_id:str;action:str;payload:dict;prev_event_hash:str|None;event_hash:str
