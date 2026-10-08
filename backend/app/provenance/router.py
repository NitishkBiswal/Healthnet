import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.provenance.schemas import ProvenanceRecord, ProvenanceResponse
from app.provenance.service import ProvenanceService
from app.security.dependencies import get_current_user
from app.security.rbac import Role

router = APIRouter(tags=["Provenance"])


def _has_any_role(user: dict, *roles: Role) -> bool:
    actual = set(user.get("roles", []))
    return any(role.value in actual for role in roles)


@router.post("/provenance", response_model=ProvenanceResponse, status_code=201)
async def record(
    request: ProvenanceRecord,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not _has_any_role(user, Role.ADMIN, Role.SYSTEM):
        raise HTTPException(status_code=403, detail="Admin or system role required")
    trusted_request = request.model_copy(update={"actor_id": str(user.get("sub", "unknown"))})
    x = await ProvenanceService(session).record_provenance(trusted_request)
    await session.commit()
    return ProvenanceResponse(id=x.id, **trusted_request.model_dump())


@router.get("/provenance/{health_id}", response_model=list[ProvenanceResponse])
async def get(
    health_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    if not _has_any_role(user, Role.ADMIN, Role.SYSTEM, Role.AUDITOR):
        raise HTTPException(status_code=403, detail="Admin, system, or auditor role required")
    return [
        ProvenanceResponse(
            id=x.id,
            health_id=x.health_id,
            repository_id=x.repository_id,
            resource_type=x.resource_type,
            resource_id=x.resource_id,
            source_system=x.source_system,
            actor_id=x.actor_id,
            action=x.action,
            details=json.loads(x.details),
        )
        for x in await ProvenanceService(session).get_provenance(health_id)
    ]
