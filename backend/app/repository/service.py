import asyncio
import ipaddress
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.fhir.client import FHIRClient
from app.record_locator.models import RecordLocator
from app.repository.models import EHRCustody, Repository
from app.repository.schemas import CustodyChangeRequest, CustodyCreate, RepositoryCreate, RepositoryStatus


async def validate_repository_url(base_url: str) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("Repository URL must use HTTP or HTTPS and include a hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Repository URL must not contain credentials, query parameters, or fragments")
    if parsed.scheme != "https" and not settings.DEBUG:
        raise ValueError("Repository URL must use HTTPS outside development")

    loop = asyncio.get_running_loop()
    try:
        answers = await loop.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except OSError as exc:
        raise ValueError("Repository hostname could not be resolved") from exc

    addresses = {answer[4][0] for answer in answers}
    if not addresses:
        raise ValueError("Repository hostname did not resolve to an address")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
            raise ValueError("Repository URL must not resolve to a private or local network")


class RepositoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_repository(self, request: RepositoryCreate) -> Repository:
        await validate_repository_url(request.base_url)
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

    async def change_custody_repository(
        self, health_id: str, request: CustodyChangeRequest
    ) -> EHRCustody:
        target = await self.session.get(Repository, request.repository_id)
        if target is None:
            raise ValueError("Target repository not found")
        if target.status == RepositoryStatus.OFFLINE.value:
            raise ValueError("Target repository is offline")
        await validate_repository_url(target.base_url)

        try:
            await FHIRClient(target.base_url).get_metadata()
        except Exception as exc:
            raise ConnectionError("Target repository could not be validated") from exc

        moment = datetime.now(UTC)
        result = await self.session.execute(
            select(EHRCustody)
            .where(EHRCustody.health_id == health_id, EHRCustody.custody_end.is_(None))
            .order_by(EHRCustody.custody_start.desc())
        )
        active = list(result.scalars())
        if active and active[0].repository_id == target.id:
            return active[0]

        for custody in active:
            custody.custody_end = moment

        locator_result = await self.session.execute(
            select(RecordLocator).where(
                RecordLocator.health_id == health_id,
                RecordLocator.status == "ACTIVE",
            )
        )
        for locator in locator_result.scalars():
            locator.status = "INACTIVE"
            locator.notes = "Superseded by repository change"
        self.session.add(
            RecordLocator(
                health_id=health_id,
                repository_id=target.id,
                endpoint=target.base_url,
                resource_types="FHIR",
                status="ACTIVE",
                last_verified_at=moment,
                notes="Selected repository after validation",
            )
        )

        replacement = EHRCustody(
            health_id=health_id,
            repository_id=target.id,
            resource_types=",".join(sorted(set(request.resource_types))),
            custody_start=moment,
        )
        self.session.add(replacement)
        await self.session.flush()
        return replacement

    async def get_custody(self, health_id: str) -> list[EHRCustody]:
        result = await self.session.execute(
            select(EHRCustody).where(EHRCustody.health_id == health_id)
        )
        return list(result.scalars())
