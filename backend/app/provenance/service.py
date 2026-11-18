import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.provenance.models import RecordProvenance
from app.provenance.schemas import FHIRProvenanceResponse, ProvenanceRecord


class ProvenanceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_provenance(self, request: ProvenanceRecord) -> RecordProvenance:
        entry = RecordProvenance(
            **request.model_dump(exclude={"details"}),
            details=json.dumps(request.details, sort_keys=True),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_provenance(self, health_id: str) -> list[RecordProvenance]:
        result = await self.session.scalars(
            select(RecordProvenance)
            .where(RecordProvenance.health_id == health_id)
            .order_by(RecordProvenance.recorded_at, RecordProvenance.id)
        )
        return list(result.all())

    @staticmethod
    def as_fhir_resource(
        entry: RecordProvenance,
    ) -> FHIRProvenanceResponse:
        return FHIRProvenanceResponse(
            id=str(entry.id),
            target=[
                {"reference": f"{entry.resource_type}/{entry.resource_id}"}
            ],
            recorded=entry.recorded_at,
            agent=[
                {
                    "who": {"identifier": {"value": entry.actor_id}},
                    "type": {
                        "text": "HealthNet user",
                    },
                }
            ],
            activity={
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-DataOperation",
                        "code": entry.action.upper(),
                        "display": entry.action,
                    }
                ]
            },
            entity=[
                {
                    "role": "source",
                    "what": {"display": entry.source_system},
                }
            ],
        )
