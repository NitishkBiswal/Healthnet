from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.consent.service import ConsentService

class AuthorizationService:
    """Backend authorization combining authenticated roles with patient consent."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def authorize_request(self, request, user: dict[str, Any]):
        roles = set(user.get("roles", []))
        if not roles:
            return False, "Authenticated principal has no HealthNet role"
        if "ADMIN" in roles or "SYSTEM" in roles:
            return True, "Privileged system role"
        if "PROVIDER" not in roles and "PATIENT" not in roles and "AUDITOR" not in roles:
            return False, "Role is not authorized for HealthNet access"
        if "PATIENT" in roles and request.grantee_id != user.get("sub"):
            return False, "Patient may only authorize access for its own principal"
        allowed = await ConsentService(self.session).check_consent(
            request.health_id, request.grantee_id, request.purpose, request.scope
        )
        if not allowed:
            return False, "No active consent for requested purpose and scope"
        return True, "Consent granted"

    async def check_permissions(self, request, user: dict[str, Any]):
        return await self.authorize_request(request, user)
