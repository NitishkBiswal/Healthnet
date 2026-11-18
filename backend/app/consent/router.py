from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.identity.models import PatientIdentity
from sqlalchemy import select
from app.consent.schemas import (
    AuthorizedPatientResponse,
    ConsentCheckRequest,
    ConsentCreateRequest,
    ConsentResponse,
)
from app.consent.service import ConsentService
from app.consent.models import Consent
from app.consent.dismissal_models import ProviderNoticeDismissal
from app.provider_trust.models import Provider
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role

router = APIRouter(tags=["Consent"])

# Build the role-checking dependencies once. These must be the actual
# FastAPI dependency callables, not wrapper functions that return them.
require_patient = require_role(Role.PATIENT)
require_provider = require_role(Role.PROVIDER)


def response(x):
    return ConsentResponse(
        id=x.id,
        health_id=x.health_id,
        grantee_type=x.grantee_type,
        grantee_id=x.grantee_id,
        purpose=x.purpose,
        scopes=x.scopes.split(",") if x.scopes else [],
        status=x.status,
        valid_from=x.valid_from,
        valid_until=x.valid_until,
        revoked_at=x.revoked_at,
        reason=x.reason,
    )


@router.post(
    "/consents",
    response_model=ConsentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consent(
    request: ConsentCreateRequest,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    owner = await session.scalar(
        select(PatientIdentity).where(
            PatientIdentity.owner_subject == user.get("sub")
        )
    )
    if owner is None or owner.display_health_id != request.health_id:
        raise HTTPException(
            403,
            "Patients may only create consent for their own Health ID",
        )

    try:
        x = await ConsentService(session).create_consent(request)
        await session.commit()
        return response(x)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/consents/{consent_id}", response_model=ConsentResponse)
async def get_consent(
    consent_id: UUID,
    _: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    x = await ConsentService(session).get_consent(consent_id)
    if x is None:
        raise HTTPException(404, "Consent not found")
    return response(x)


@router.delete("/consents/{consent_id}", response_model=ConsentResponse)
async def revoke_consent(
    consent_id: UUID,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    x = await ConsentService(session).get_consent(consent_id)
    if x is None:
        raise HTTPException(404, "Consent not found")

    owner = await session.scalar(
        select(PatientIdentity).where(
            PatientIdentity.owner_subject == user.get("sub")
        )
    )
    if owner is None or owner.display_health_id != x.health_id:
        raise HTTPException(403, "Patients may only revoke their own consent")

    x = await ConsentService(session).revoke_consent(consent_id)
    await session.commit()
    return response(x)


@router.get(
    "/patients/{health_id}/consents",
    response_model=list[ConsentResponse],
)
async def get_patient_consents(
    health_id: str,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    owner = await session.scalar(
        select(PatientIdentity).where(
            PatientIdentity.owner_subject == user.get("sub")
        )
    )
    if owner is None or owner.display_health_id != health_id:
        raise HTTPException(403, "Patients may only view their own consent")

    return [
        response(x)
        for x in await ConsentService(session).get_patient_consents(health_id)
    ]


@router.get(
    "/authorized-patients",
    response_model=list[AuthorizedPatientResponse],
)
async def authorized_patients(
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    rows = await ConsentService(session).get_authorized_patients(
        user.get("sub", "")
    )
    # Persist any stale grants revoked because a completed repository migration
    # occurred after the original consent was issued.
    await session.commit()
    return [
        AuthorizedPatientResponse(
            health_id=patient.display_health_id,
            given_name=patient.given_name,
            family_name=patient.family_name,
            consent_id=consent.id,
            purpose=consent.purpose,
            scopes=consent.scopes.split(",") if consent.scopes else [],
            valid_from=consent.valid_from,
            valid_until=consent.valid_until,
            status=consent.status,
            reason=consent.reason,
        )
        for consent, patient in rows
    ]


@router.post("/consents/check")
async def check_consent(
    request: ConsentCheckRequest,
    _: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    allowed = await ConsentService(session).check_consent(
        request.health_id,
        request.grantee_id,
        request.purpose,
        request.scope,
        request.at,
    )
    return {"allowed": allowed}


@router.post("/provider-notices/{consent_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_provider_notice(
    consent_id: UUID,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    """Hide a revoked migration notice for this provider only; preserve consent/audit history."""
    subject = str(user.get("sub") or "")
    provider = await session.scalar(
        select(Provider).where(
            Provider.keycloak_subject == subject,
            Provider.trust_status == "ACTIVE",
        )
    )
    consent = await session.get(Consent, consent_id)
    if (
        provider is None
        or consent is None
        or consent.grantee_type != "PROVIDER"
        or consent.grantee_id != provider.external_id
        or consent.status != "REVOKED"
        or not (consent.reason or "").startswith("REPOSITORY_CHANGED:")
    ):
        raise HTTPException(404, "Revoked repository-change notice not found")

    existing = await session.get(ProviderNoticeDismissal, (consent_id, subject))
    if existing is None:
        session.add(ProviderNoticeDismissal(consent_id=consent_id, provider_subject=subject))
        await session.commit()
