import hashlib,json
from uuid import UUID
from sqlalchemy import desc,select
from sqlalchemy.ext.asyncio import AsyncSession
from app.audit.models import AuditEvent
class AuditService:
    def __init__(self,session:AsyncSession):self.session=session
    async def log_event(self,request):
        previous=await self.session.scalar(select(AuditEvent).order_by(desc(AuditEvent.created_at),desc(AuditEvent.id)))
        prev=previous.event_hash if previous else ""
        payload=json.dumps(request.payload,sort_keys=True,separators=(",",":"))
        digest=hashlib.sha256(f"{prev}|{request.event_type.value}|{request.actor_id}|{request.action}|{payload}".encode()).hexdigest()
        x=AuditEvent(event_type=request.event_type.value,health_id=request.health_id,actor_id=request.actor_id,action=request.action,payload=payload,prev_event_hash=prev or None,event_hash=digest)
        self.session.add(x);await self.session.flush();return x
    async def get_event(self,event_id:UUID):return await self.session.get(AuditEvent,event_id)
    async def get_patient_events(self,health_id:str):
        result=await self.session.execute(select(AuditEvent).where(AuditEvent.health_id==health_id).order_by(AuditEvent.created_at));return list(result.scalars())
    async def verify_chain_integrity(self):
        result=await self.session.execute(select(AuditEvent).order_by(AuditEvent.created_at,AuditEvent.id));previous=""
        for x in result.scalars():
            expected=hashlib.sha256(f"{previous}|{x.event_type}|{x.actor_id}|{x.action}|{x.payload}".encode()).hexdigest()
            if expected!=x.event_hash or (x.prev_event_hash or "")!=previous:return False
            previous=x.event_hash
        return True
