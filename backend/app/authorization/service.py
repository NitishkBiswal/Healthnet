from sqlalchemy.ext.asyncio import AsyncSession
from app.consent.service import ConsentService

class AuthorizationService:
    def __init__(self,session:AsyncSession): self.session=session
    async def authorize_request(self,request):
        if request.role not in {"PATIENT","PROVIDER","ADMIN","AUDITOR","SYSTEM"}:
            return False,"Unknown role"
        if request.role in {"ADMIN","SYSTEM"}:
            return True,"Privileged system role"
        allowed=await ConsentService(self.session).check_consent(request.health_id,request.grantee_id,request.purpose,request.scope)
        if not allowed:return False,"No active consent for requested purpose and scope"
        return True,"Consent granted"
    async def check_permissions(self,request): return await self.authorize_request(request)
