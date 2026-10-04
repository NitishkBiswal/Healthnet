import json
from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.provenance.schemas import ProvenanceRecord,ProvenanceResponse
from app.provenance.service import ProvenanceService
router=APIRouter(tags=["Provenance"])
@router.post("/provenance",response_model=ProvenanceResponse,status_code=201)
async def record(request:ProvenanceRecord,session:AsyncSession=Depends(get_db)):
    x=await ProvenanceService(session).record_provenance(request);await session.commit()
    return ProvenanceResponse(id=x.id,**request.model_dump())
@router.get("/provenance/{health_id}",response_model=list[ProvenanceResponse])
async def get(health_id:str,session:AsyncSession=Depends(get_db)):
    return [ProvenanceResponse(id=x.id,health_id=x.health_id,repository_id=x.repository_id,resource_type=x.resource_type,resource_id=x.resource_id,source_system=x.source_system,actor_id=x.actor_id,action=x.action,details=json.loads(x.details)) for x in await ProvenanceService(session).get_provenance(health_id)]
