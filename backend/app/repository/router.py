from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.repository.schemas import CustodyCreate, CustodyResponse, RepositoryCreate, RepositoryInfo, RepositoryStatus
from app.repository.service import RepositoryService

router = APIRouter(tags=["Repositories"])

@router.post("/repositories", response_model=RepositoryInfo, status_code=status.HTTP_201_CREATED)
async def create_repository(request: RepositoryCreate, session: AsyncSession = Depends(get_db)):
    try:
        item = await RepositoryService(session).register_repository(request); await session.commit()
        return RepositoryInfo.model_validate(item)
    except ValueError as exc:
        await session.rollback(); raise HTTPException(409, str(exc)) from exc

@router.get("/repositories", response_model=list[RepositoryInfo])
async def list_repositories(session: AsyncSession = Depends(get_db)):
    return [RepositoryInfo.model_validate(x) for x in await RepositoryService(session).list_repositories()]

@router.get("/repositories/{repository_id}", response_model=RepositoryInfo)
async def get_repository(repository_id: UUID, session: AsyncSession = Depends(get_db)):
    item = await RepositoryService(session).get_repository(repository_id)
    if item is None: raise HTTPException(404, "Repository not found")
    return RepositoryInfo.model_validate(item)

@router.post("/repositories/{repository_id}/availability", response_model=RepositoryInfo)
async def set_repository_availability(repository_id: UUID, status_value: RepositoryStatus, session: AsyncSession = Depends(get_db)):
    service=RepositoryService(session); item=await service.get_repository(repository_id)
    if item is None: raise HTTPException(404, "Repository not found")
    await service.check_availability(item,status_value); await session.commit()
    return RepositoryInfo.model_validate(item)

@router.post("/ehr-custody", response_model=CustodyResponse, status_code=status.HTTP_201_CREATED)
async def create_custody(request: CustodyCreate, session: AsyncSession = Depends(get_db)):
    try:
        item=await RepositoryService(session).register_custody(request); await session.commit()
        return CustodyResponse(id=item.id,health_id=item.health_id,repository_id=item.repository_id,
            resource_types=item.resource_types.split(","),custody_start=item.custody_start,custody_end=item.custody_end)
    except ValueError as exc:
        await session.rollback(); raise HTTPException(400,str(exc)) from exc

@router.get("/patients/{health_id}/ehr-custody", response_model=list[CustodyResponse])
async def get_custody(health_id: str, session: AsyncSession = Depends(get_db)):
    items=await RepositoryService(session).get_custody(health_id)
    return [CustodyResponse(id=x.id,health_id=x.health_id,repository_id=x.repository_id,resource_types=x.resource_types.split(",") if x.resource_types else [],custody_start=x.custody_start,custody_end=x.custody_end) for x in items]
