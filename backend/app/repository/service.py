from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.models import EHRCustody, Repository
from app.repository.schemas import CustodyCreate, RepositoryCreate, RepositoryStatus


class RepositoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_repository(self, request: RepositoryCreate) -> Repository:
        existing = await self.session.scalar(
            select(Repository).where(Repository.code == request.code)
        )
        if existing:
            raise ValueError("Repository code already exists")
        repository = Repository(
            code=request.code,
            name=request.name,
            jurisdiction=request.jurisdiction,
            base_url=request.base_url,
            description=request.description,
            status=RepositoryStatus.ONLINE.value,
        )
        self.session.add(repository)
        await self.session.flush()
        return repository

    async def get_repository(self, repository_id: UUID) -> Repository | None:
        return await self.session.get(Repository, repository_id)

    async def list_repositories(self) -> list[Repository]:
        result = await self.session.execute(select(Repository).order_by(Repository.code))
        return list(result.scalars())

    async def check_availability(self, repository: Repository, status: RepositoryStatus) -> Repository:
        repository.status = status.value
        repository.last_checked_at = datetime.now(UTC)
        await self.session.flush()
        return repository

    async def register_custody(self, request: CustodyCreate) -> EHRCustody:
        repository = await self.session.get(Repository, request.repository_id)
        if repository is None:
            raise ValueError("Repository not found")
        custody = EHRCustody(
            health_id=request.health_id,
            repository_id=request.repository_id,
            resource_types=",".join(sorted(set(request.resource_types))),
            custody_start=request.custody_start,
            custody_end=request.custody_end,
        )
        self.session.add(custody)
        await self.session.flush()
        return custody

    async def get_custody(self, health_id: str) -> list[EHRCustody]:
        result = await self.session.execute(
            select(EHRCustody).where(EHRCustody.health_id == health_id)
        )
        return list(result.scalars())
