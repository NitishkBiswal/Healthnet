import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.provenance.models import RecordProvenance
class ProvenanceService:
    def __init__(self,session:AsyncSession):self.session=session
    async def record_provenance(self,request):
        x=RecordProvenance(**request.model_dump(exclude={"details"}),details=json.dumps(request.details,sort_keys=True));self.session.add(x);await self.session.flush();return x
    async def get_provenance(self,health_id:str):
        result=await self.session.execute(select(RecordProvenance).where(RecordProvenance.health_id==health_id).order_by(RecordProvenance.recorded_at));return list(result.scalars())
