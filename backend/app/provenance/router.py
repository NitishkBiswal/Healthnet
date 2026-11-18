from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent.service import ConsentService
from app.core.database import get_db
from app.identity.models import PatientIdentity
from app.provenance.schemas import (
    FHIRProvenanceResponse,
    ProvenanceCreateRequest,
    ProvenanceRecord,
    ProvenanceResponse,
)
from app.provenance.service import ProvenanceService
from app.provider_trust.models import Provider
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role

router = APIRouter(tags=["Provenance"])
require_provider = require_role(Role.PROVIDER)


@router.post(
    "/provenance",
    response_model=ProvenanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record(
    request: ProvenanceCreateRequest,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    provider = await session.scalar(
        select(Provider).where(
            Provider.keycloak_subject == user.get("sub"),
            Provider.trust_status == "ACTIVE",
        )
    )
    if provider is None:
        raise HTTPException(403, "No active trusted provider is linked to this account")
    allowed = await ConsentService(session).check_consent(
        request.health_id, provider.external_id, "TREATMENT", request.resource_type.lower()
    ) or await ConsentService(session).check_consent(
        request.health_id, provider.external_id, "TREATMENT", "full"
    )
    if not allowed:
        raise HTTPException(403, "Active treatment consent is required")
    entry = await ProvenanceService(session).record_provenance(
        ProvenanceRecord(
            **request.model_dump(),
            actor_id=str(user.get("sub", "unknown")),
        )
    )
    await session.commit()
    return ProvenanceResponse(
        id=entry.id,
        recorded_at=entry.recorded_at,
        **request.model_dump(),
        actor_id=str(user.get("sub", "unknown")),
    )


@router.get(
    "/provenance/{health_id}",
    response_model=list[FHIRProvenanceResponse],
)
async def get(
    health_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    roles = set(user.get("roles", []))
    if Role.PATIENT.value in roles:
        owner = await session.scalar(
            select(PatientIdentity).where(
                PatientIdentity.display_health_id == health_id,
                PatientIdentity.owner_subject == user.get("sub"),
            )
        )
        if owner is None:
            raise HTTPException(403, "Patients may only view their own record history")
    elif Role.PROVIDER.value in roles:
        provider = await session.scalar(
            select(Provider).where(
                Provider.keycloak_subject == user.get("sub"),
                Provider.trust_status == "ACTIVE",
            )
        )
        if provider is None:
            raise HTTPException(403, "No active trusted provider is linked to this account")
        consent = ConsentService(session)
        allowed = await consent.check_consent(
            health_id, provider.external_id, "TREATMENT", "clinical"
        ) or await consent.check_consent(
            health_id, provider.external_id, "TREATMENT", "full"
        )
        if not allowed:
            raise HTTPException(403, "Active treatment consent is required")
    elif Role.AUDITOR.value not in roles and Role.ADMIN.value not in roles:
        raise HTTPException(403, "A patient, provider, auditor, or admin role is required")

    entries = await ProvenanceService(session).get_provenance(health_id)
    return [ProvenanceService.as_fhir_resource(entry) for entry in entries]
