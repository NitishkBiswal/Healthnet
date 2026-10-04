from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.longitudinal.schemas import LongitudinalViewRequest,LongitudinalViewResponse
from app.longitudinal.service import LongitudinalViewService
router=APIRouter(tags=["Longitudinal"])
@router.post("/patients/longitudinal-view",response_model=LongitudinalViewResponse)
async def longitudinal_view(request:LongitudinalViewRequest,session:AsyncSession=Depends(get_db)):
    result=await LongitudinalViewService(session).build_longitudinal_view(request)
    return LongitudinalViewResponse(health_id=result[0],completeness=result[1],records=result[2],repositories_checked=result[3],repositories_available=result[4],errors=result[5])
