from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.authorization.schemas import AuthorizationDecision, AuthorizationRequest
from app.authorization.service import AuthorizationService
from app.core.database import get_db

router=APIRouter(tags=["Authorization"])

@router.post("/check",response_model=AuthorizationDecision)
async def authorize(request:AuthorizationRequest,session:AsyncSession=Depends(get_db)):
    allowed,reason=await AuthorizationService(session).authorize_request(request)
    return AuthorizationDecision(allowed=allowed,reason=reason)
