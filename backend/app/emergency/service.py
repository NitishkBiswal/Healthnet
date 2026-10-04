from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.emergency.models import EmergencyHealthProfile,BreakGlassEvent
class EmergencyService:
    def __init__(self,session:AsyncSession):self.session=session
    async def get_emergency_profile(self,health_id:str):
        return await self.session.scalar(select(EmergencyHealthProfile).where(EmergencyHealthProfile.health_id==health_id))
    async def invoke_break_glass(self,health_id:str,actor_id:str,reason:str):
        event=BreakGlassEvent(health_id=health_id,actor_id=actor_id,reason=reason);self.session.add(event);await self.session.flush();return event
