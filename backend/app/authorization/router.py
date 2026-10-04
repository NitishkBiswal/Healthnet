from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.authorization.schemas import AuthorizationDecision, AuthorizationRequest
from app.authorization.service import AuthorizationService
from app.core.database import get_db
from app.security.dependencies import get_current_user

router = APIRouter(tags=["Authorization"])

@router.post("/check", response_model=AuthorizationDecision)
async def authorize(
    request: AuthorizationRequest,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    allowed, reason = await AuthorizationService(session).authorize_request(request, user)
    return AuthorizationDecision(allowed=allowed, reason=reason)

@router.get("/me")
async def current_principal(user: dict = Depends(get_current_user)):
    return {"subject": user.get("sub"), "email": user.get("email"), "roles": user.get("roles", [])}
