from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.identity.models import PatientIdentity
from app.repository.schemas import CustodyChangeRequest, CustodyCreate, CustodyResponse, RepositoryCreate, RepositoryInfo, RepositoryStatus
from app.repository.service import RepositoryService
from app.security.dependencies import require_role
from app.security.rbac import Role
router = APIRouter(tags=["Repositories"])
require_admin = require_role(Role.ADMIN)
@router.post("/repositories", response_model=RepositoryInfo, status_code=status.HTTP_201_CREATED)
async def create_repository(request: RepositoryCreate, _: dict = Depends(require_admin), session: AsyncSession = Depends(get_db)):
    try:
        item = await RepositoryService(session).register_repository(request); await session.commit(); return RepositoryInfo.model_validate(item)
    except ValueError as exc:
        await session.rollback(); raise HTTPException(409, str(exc)) from exc
@router.get("/repositories", response_model=list[RepositoryInfo])
async def list_repositories(_: dict = Depends(require_admin), session: AsyncSession = Depends(get_db)):
    return [RepositoryInfo.model_validate(x) for x in await RepositoryService(session).list_repositories()]
@router.get("/repositories/{repository_id}", response_model=RepositoryInfo)
async def get_repository(repository_id: UUID, _: dict = Depends(require_admin), session: AsyncSession = Depends(get_db)):
    item = await RepositoryService(session).get_repository(repository_id)
    if item is None: raise HTTPException(404, "Repository not found")
    return RepositoryInfo.model_validate(item)
@router.post("/repositories/{repository_id}/availability", response_model=RepositoryInfo)
async def set_repository_availability(repository_id: UUID, status_value: RepositoryStatus, _: dict = Depends(require_admin), session: AsyncSession = Depends(get_db)):
    service = RepositoryService(session); item = await service.get_repository(repository_id)
    if item is None: raise HTTPException(404, "Repository not found")
    await service.check_availability(item, status_value); await session.commit(); return RepositoryInfo.model_validate(item)
@router.post("/ehr-custody", response_model=CustodyResponse, status_code=status.HTTP_201_CREATED)
async def create_custody(request: CustodyCreate, _: dict = Depends(require_admin), session: AsyncSession = Depends(get_db)):
    try:
        item = await RepositoryService(session).register_custody(request); await session.commit()
        return CustodyResponse(id=item.id, health_id=item.health_id, repository_id=item.repository_id, resource_types=item.resource_types.split(","), custody_start=item.custody_start, custody_end=item.custody_end)
    except ValueError as exc:
        await session.rollback(); raise HTTPException(400, str(exc)) from exc
@router.put("/patients/{health_id}/ehr-custody", response_model=CustodyResponse)
async def change_custody_repository(
    health_id: str,
    request: CustodyChangeRequest,
    user: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    patient = await session.scalar(
        select(PatientIdentity).where(PatientIdentity.display_health_id == health_id)
    )
    if patient is None:
        raise HTTPException(404, "Patient not found")
    try:
        item = await RepositoryService(session).change_custody_repository(health_id, request)
        await AuditService(session).log_event(
            AuditEventCreate(
                event_type=AuditEventType.REPOSITORY_CHANGE,
                health_id=health_id,
                actor_id=user.get("sub", "unknown"),
                action="active repository changed",
                payload={"repository_id": str(request.repository_id)},
            )
        )
        await session.commit()
        return CustodyResponse(id=item.id, health_id=item.health_id, repository_id=item.repository_id, resource_types=item.resource_types.split(","), custody_start=item.custody_start, custody_end=item.custody_end)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc
    except ConnectionError as exc:
        await session.rollback()
        raise HTTPException(502, str(exc)) from exc

@router.get("/patients/{health_id}/ehr-custody", response_model=list[CustodyResponse])
async def get_custody(health_id: str, _: dict = Depends(require_admin), session: AsyncSession = Depends(get_db)):
    items = await RepositoryService(session).get_custody(health_id)
    return [CustodyResponse(id=x.id, health_id=x.health_id, repository_id=x.repository_id, resource_types=x.resource_types.split(",") if x.resource_types else [], custody_start=x.custody_start, custody_end=x.custody_end) for x in items]