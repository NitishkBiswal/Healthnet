from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.record_locator.models import RecordLocator
from app.repository.models import Repository

class RecordLocatorService:
    def __init__(self, session: AsyncSession):
        self.session = session
    async def register_location(self, health_id: str, data) -> RecordLocator:
        repository = await self.session.get(Repository, data.repository_id)
        if repository is None:
            raise ValueError("Repository not found")
        if repository.status == "OFFLINE":
            raise ValueError("Repository is offline")
        location = RecordLocator(health_id=health_id, repository_id=data.repository_id, endpoint=data.endpoint,
            resource_types=",".join(sorted(set(data.resource_types))), status=data.status,
            notes=data.notes, last_verified_at=datetime.now(UTC))
        self.session.add(location)
        await self.session.flush()
        return location
    async def get_locations(self, health_id: str) -> list[RecordLocator]:
        result = await self.session.execute(select(RecordLocator).where(RecordLocator.health_id == health_id).order_by(RecordLocator.created_at))
        return list(result.scalars())
    async def update_location(self, location_id: UUID, data) -> RecordLocator:
        location = await self.session.get(RecordLocator, location_id)
        if location is None:
            raise ValueError("Record location not found")
        location.endpoint = data.endpoint
        location.resource_types = ",".join(sorted(set(data.resource_types)))
        location.status = data.status
        location.notes = data.notes
        location.last_verified_at = datetime.now(UTC)
        await self.session.flush()
        return location
