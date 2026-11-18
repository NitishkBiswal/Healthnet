from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.record_locator.models import RecordLocator
from app.repository.models import Repository


class RecordLocatorService:
    """Maintains the single authoritative clinical repository for each patient."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_location(self, health_id: str, data) -> RecordLocator:
        repository = await self.session.get(Repository, data.repository_id)
        if repository is None:
            raise ValueError("Repository not found")
        if repository.status == "OFFLINE":
            raise ValueError("Repository is offline")

        if data.status == "ACTIVE":
            await self.session.execute(
                update(RecordLocator)
                .where(
                    RecordLocator.health_id == health_id,
                    RecordLocator.status == "ACTIVE",
                )
                .values(status="INACTIVE")
            )

        location = RecordLocator(
            health_id=health_id,
            repository_id=data.repository_id,
            endpoint=data.endpoint or repository.base_url,
            resource_types=",".join(sorted(set(data.resource_types))),
            status=data.status,
            notes=data.notes,
            last_verified_at=datetime.now(UTC),
        )
        self.session.add(location)
        await self.session.flush()
        return location

    async def get_locations(self, health_id: str) -> list[RecordLocator]:
        result = await self.session.execute(
            select(RecordLocator)
            .where(RecordLocator.health_id == health_id)
            .order_by(RecordLocator.created_at)
        )
        return list(result.scalars())

    async def get_current_location(self, health_id: str) -> RecordLocator | None:
        return await self.session.scalar(
            select(RecordLocator)
            .where(
                RecordLocator.health_id == health_id,
                RecordLocator.status == "ACTIVE",
            )
            .order_by(RecordLocator.created_at.desc())
        )

    async def set_current_location(
        self,
        health_id: str,
        repository_id: UUID,
        endpoint: str,
        resource_types: list[str],
        notes: str | None = None,
    ) -> RecordLocator:
        repository = await self.session.get(Repository, repository_id)
        if repository is None:
            raise ValueError("Destination repository not found")
        if repository.status == "OFFLINE":
            raise ValueError("Destination repository is offline")

        await self.session.execute(
            update(RecordLocator)
            .where(
                RecordLocator.health_id == health_id,
                RecordLocator.status == "ACTIVE",
            )
            .values(status="INACTIVE")
        )

        location = RecordLocator(
            health_id=health_id,
            repository_id=repository_id,
            endpoint=endpoint or repository.base_url,
            resource_types=",".join(sorted(set(resource_types))),
            status="ACTIVE",
            notes=notes,
            last_verified_at=datetime.now(UTC),
        )
        self.session.add(location)
        await self.session.flush()
        return location

    async def update_location(self, location_id: UUID, data) -> RecordLocator:
        location = await self.session.get(RecordLocator, location_id)
        if location is None:
            raise ValueError("Record location not found")

        if data.status == "ACTIVE":
            await self.session.execute(
                update(RecordLocator)
                .where(
                    RecordLocator.health_id == location.health_id,
                    RecordLocator.id != location.id,
                    RecordLocator.status == "ACTIVE",
                )
                .values(status="INACTIVE")
            )

        location.endpoint = data.endpoint
        location.resource_types = ",".join(sorted(set(data.resource_types)))
        location.status = data.status
        location.notes = data.notes
        location.last_verified_at = datetime.now(UTC)
        await self.session.flush()
        return location
