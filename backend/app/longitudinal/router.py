from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.longitudinal.schemas import LongitudinalViewRequest, LongitudinalViewResponse
from app.longitudinal.service import LongitudinalViewService

router = APIRouter(tags=["Longitudinal"])

@router.post("/patients/longitudinal-view", response_model=LongitudinalViewResponse)
async def longitudinal_view(
    request: LongitudinalViewRequest,
    session: AsyncSession = Depends(get_db),
) -> LongitudinalViewResponse:
    return await LongitudinalViewService(session).build_longitudinal_view(request)
