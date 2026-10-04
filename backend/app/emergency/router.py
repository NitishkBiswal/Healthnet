from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.emergency.schemas import BreakGlassRequest,EmergencyProfileResponse
from app.emergency.service import EmergencyService
router=APIRouter(tags=["Emergency"])
def response(x):
    return EmergencyProfileResponse(health_id=x.health_id,blood_group=x.blood_group,allergies=[v for v in x.allergies.split(",") if v],medications=[v for v in x.medications.split(",") if v],conditions=[v for v in x.conditions.split(",") if v],emergency_contacts=[v for v in x.emergency_contacts.split(",") if v])
@router.get("/patients/{health_id}/emergency-profile",response_model=EmergencyProfileResponse)
async def get_emergency_profile(health_id:str,session:AsyncSession=Depends(get_db)):
    x=await EmergencyService(session).get_emergency_profile(health_id)
    if x is None:raise HTTPException(404,"Emergency profile not found")
    return response(x)
@router.post("/patients/{health_id}/break-glass")
async def invoke_break_glass(health_id:str,request:BreakGlassRequest,session:AsyncSession=Depends(get_db)):
    x=await EmergencyService(session).invoke_break_glass(health_id,request.actor_id,request.reason);await session.commit()
    return {"event_id":x.id,"health_id":health_id,"tier":request.tier,"status":"BREAK_GLASS_GRANTED"}
