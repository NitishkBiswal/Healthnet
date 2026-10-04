from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.record_locator.schemas import RecordLocationEntry, RecordLocationResponse
from app.record_locator.service import RecordLocatorService

router=APIRouter(tags=["Record Locator"])

def _response(x):
    return RecordLocationResponse(id=x.id,health_id=x.health_id,repository_id=x.repository_id,endpoint=x.endpoint,
        resource_types=x.resource_types.split(",") if x.resource_types else [],status=x.status,last_verified_at=x.last_verified_at,notes=x.notes)

@router.post("/patients/{health_id}/record-locations",response_model=RecordLocationResponse,status_code=status.HTTP_201_CREATED)
async def create_record_location(health_id:str,request:RecordLocationEntry,session:AsyncSession=Depends(get_db)):
    try:
        x=await RecordLocatorService(session).register_location(health_id,request); await session.commit(); return _response(x)
    except ValueError as exc:
        await session.rollback(); raise HTTPException(400,str(exc)) from exc

@router.get("/patients/{health_id}/record-locations",response_model=list[RecordLocationResponse])
async def get_record_locations(health_id:str,session:AsyncSession=Depends(get_db)):
    return [_response(x) for x in await RecordLocatorService(session).get_locations(health_id)]

@router.put("/record-locations/{location_id}",response_model=RecordLocationResponse)
async def update_record_location(location_id:UUID,request:RecordLocationEntry,session:AsyncSession=Depends(get_db)):
    try:
        x=await RecordLocatorService(session).update_location(location_id,request); await session.commit(); return _response(x)
    except ValueError as exc:
        await session.rollback(); raise HTTPException(404,str(exc)) from exc
