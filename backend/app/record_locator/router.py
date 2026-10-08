from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent.models import Consent
from app.core.database import get_db
from app.identity.models import PatientIdentity
from app.provider_trust.models import Provider
from app.record_locator.schemas import (
    CurrentRecordLocationResponse,
    RecordLocationEntry,
    RecordLocationResponse,
)
from app.record_locator.service import RecordLocatorService
from app.repository.models import Repository
from app.security.dependencies import get_current_user
from app.security.rbac import Role

router = APIRouter(tags=["Record Locator"])


def _response(x):
    return RecordLocationResponse(
        id=x.id,
        health_id=x.health_id,
        repository_id=x.repository_id,
        endpoint=x.endpoint,
        resource_types=x.resource_types.split(",") if x.resource_types else [],
        status=x.status,
        last_verified_at=x.last_verified_at,
        notes=x.notes,
    )


def _admin_or_system(user: dict) -> bool:
    roles = set(user.get("roles", []))
    return Role.ADMIN.value in roles or Role.SYSTEM.value in roles


async def _authorize_location_read(health_id: str, user: dict, session: AsyncSession) -> None:
    roles = set(user.get("roles", []))
    if _admin_or_system(user) or Role.AUDITOR.value in roles:
        return

    subject = str(user.get("sub", ""))
    if Role.PATIENT.value in roles:
        patient = await session.scalar(
            select(PatientIdentity).where(PatientIdentity.owner_subject == subject)
        )
        if patient is not None and patient.display_health_id == health_id:
            return
        raise HTTPException(status_code=403, detail="Patients can only view their own repository assignment")

    if Role.PROVIDER.value in roles:
        provider = await session.scalar(
            select(Provider).where(
                Provider.keycloak_subject == subject,
                Provider.trust_status == "ACTIVE",
            )
        )
        if provider is not None:
            now = datetime.now(UTC)
            consent = await session.scalar(
                select(Consent.id).where(
                    Consent.health_id == health_id,
                    Consent.grantee_type == "PROVIDER",
                    Consent.grantee_id == provider.external_id,
                    Consent.status == "ACTIVE",
                    Consent.valid_from <= now,
                    (Consent.valid_until.is_(None) | (Consent.valid_until >= now)),
                ).limit(1)
            )
            if consent is not None:
                return
        raise HTTPException(status_code=403, detail="Active patient consent is required to view this repository assignment")

    raise HTTPException(status_code=403, detail="Role is not permitted to view repository assignments")


async def _require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not _admin_or_system(user):
        raise HTTPException(status_code=403, detail="Admin or system role required")
    return user


@router.post(
    "/patients/{health_id}/record-locations",
    response_model=RecordLocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_record_location(
    health_id: str,
    request: RecordLocationEntry,
    _: dict = Depends(_require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        x = await RecordLocatorService(session).register_location(health_id, request)
        await session.commit()
        return _response(x)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get(
    "/patients/{health_id}/record-locations",
    response_model=list[RecordLocationResponse],
)
async def get_record_locations(
    health_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await _authorize_location_read(health_id, user, session)
    return [_response(x) for x in await RecordLocatorService(session).get_locations(health_id)]


@router.get(
    "/patients/{health_id}/current",
    response_model=CurrentRecordLocationResponse,
)
async def get_current_record_location(
    health_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await _authorize_location_read(health_id, user, session)
    location = await RecordLocatorService(session).get_current_location(health_id)
    if location is None:
        raise HTTPException(404, "No current repository is assigned to this patient")

    repository = await session.get(Repository, location.repository_id)
    if repository is None:
        raise HTTPException(404, "Current repository is not registered")

    return CurrentRecordLocationResponse(
        health_id=health_id,
        repository_id=repository.id,
        repository_code=repository.code,
        repository_name=repository.name,
        jurisdiction=repository.jurisdiction,
        endpoint=location.endpoint,
        resource_types=location.resource_types.split(",") if location.resource_types else [],
        assigned_at=location.created_at,
    )


@router.put("/record-locations/{location_id}", response_model=RecordLocationResponse)
async def update_record_location(
    location_id: UUID,
    request: RecordLocationEntry,
    _: dict = Depends(_require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        x = await RecordLocatorService(session).update_location(location_id, request)
        await session.commit()
        return _response(x)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(404, str(exc)) from exc
