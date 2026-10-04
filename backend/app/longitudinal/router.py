from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.longitudinal.schemas import LongitudinalViewRequest, LongitudinalViewResponse
from app.longitudinal.service import LongitudinalAccessDenied, LongitudinalViewService
from app.security.dependencies import get_current_user

router = APIRouter(tags=["Longitudinal"])


@router.post("/patients/longitudinal-view", response_model=LongitudinalViewResponse)
async def longitudinal_view(
    request: LongitudinalViewRequest,
    user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LongitudinalViewResponse:
    try:
        return await LongitudinalViewService(session).build_longitudinal_view(
            request, user
        )
    except LongitudinalAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
