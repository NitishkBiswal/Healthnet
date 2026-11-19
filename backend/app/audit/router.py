import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent
from app.audit.schemas import AuditEventCreate, AuditEventResponse
from app.audit.service import AuditService
from app.core.database import get_db
from app.security.dependencies import require_role
from app.security.rbac import Role


router = APIRouter(tags=["Audit"])
require_auditor = require_role(Role.AUDITOR)


def response(x):
    return AuditEventResponse(
        id=x.id,
        event_type=x.event_type,
        health_id=x.health_id,
        actor_id=x.actor_id,
        action=x.action,
        payload=json.loads(x.payload),
        prev_event_hash=x.prev_event_hash,
        event_hash=x.event_hash,
        created_at=x.created_at,
    )


@router.post("", response_model=AuditEventResponse, status_code=201)
async def log(
    request: AuditEventCreate,
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
):
    x = await AuditService(session).log_event(request)
    await session.commit()
    return response(x)


@router.get("/{event_id}", response_model=AuditEventResponse)
async def get(
    event_id: UUID,
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
):
    x = await AuditService(session).get_event(event_id)
    if x is None:
        raise HTTPException(404, "Audit event not found")
    return response(x)


@router.get("/patient/{health_id}", response_model=list[AuditEventResponse])
async def patient(
    health_id: str,
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
):
    return [response(x) for x in await AuditService(session).get_patient_events(health_id)]


@router.get("/integrity")
async def integrity(
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
):
    return {"valid": await AuditService(session).verify_chain_integrity()}


@router.get("/emergency-access", response_model=list[AuditEventResponse])
async def emergency_access_events(
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
):
    """List break-glass declarations and chronic-summary reads for oversight."""
    result = await session.execute(
        select(AuditEvent)
        .where(
            AuditEvent.action.in_(
                [
                    "BREAK_GLASS_INVOKED",
                    "BREAK_GLASS_CHRONIC_SUMMARY_VIEWED",
                ]
            )
        )
        .order_by(desc(AuditEvent.created_at))
        .limit(500)
    )
    return [response(event) for event in result.scalars().all()]


@router.get("/imports")
async def imported_records(
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(AuditEvent)
        .where(AuditEvent.action == "MEDICAL_RECORD_IMPORTED")
        .order_by(desc(AuditEvent.created_at))
        .limit(500)
    )
    return [response(event) for event in result.scalars().all()]
