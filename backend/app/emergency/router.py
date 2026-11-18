from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent.service import ConsentService
from app.core.database import get_db
from app.emergency.schemas import (
    BreakGlassRequest,
    BreakGlassResponse,
    EmergencyProfileRequest,
    EmergencyProfileResponse,
    PatientNotificationResponse,
)
from app.emergency.service import EmergencyService
from app.identity.models import PatientIdentity
from app.provider_trust.models import Provider
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role

router = APIRouter(tags=["Emergency"])
require_provider = require_role(Role.PROVIDER)
require_patient = require_role(Role.PATIENT)


def _profile_response(profile) -> EmergencyProfileResponse:
    return EmergencyProfileResponse(
        health_id=profile.health_id,
        blood_group=profile.blood_group,
        updated_at=profile.updated_at,
        **EmergencyService.profile_lists(profile),
    )


async def _owned_patient(
    health_id: str, user: dict, session: AsyncSession
) -> PatientIdentity:
    patient = await session.scalar(
        select(PatientIdentity).where(
            PatientIdentity.display_health_id == health_id,
            PatientIdentity.owner_subject == user.get("sub"),
        )
    )
    if patient is None:
        raise HTTPException(403, "Patients may only access their own emergency profile")
    return patient


@router.get(
    "/patients/{health_id}/emergency-profile",
    response_model=EmergencyProfileResponse,
)
async def get_emergency_profile(
    health_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    break_glass_token: str | None = Header(default=None, alias="X-Break-Glass-Token"),
):
    roles = set(user.get("roles", []))
    if Role.PATIENT.value in roles:
        await _owned_patient(health_id, user, session)
    elif Role.PROVIDER.value in roles:
        provider = await session.scalar(
            select(Provider).where(
                Provider.keycloak_subject == user.get("sub"),
                Provider.trust_status == "ACTIVE",
            )
        )
        if provider is None:
            raise HTTPException(403, "No active trusted provider is linked to this account")
        allowed = await ConsentService(session).check_consent(
            health_id, provider.external_id, "EMERGENCY", "clinical"
        )
        if not allowed and not await EmergencyService(session).validate_break_glass(
            health_id, str(user.get("sub", "")), break_glass_token
        ):
            raise HTTPException(403, "Emergency profile requires consent or active break-glass access")
    else:
        raise HTTPException(403, "Patient or provider role required")

    profile = await EmergencyService(session).get_emergency_profile(health_id)
    if profile is None:
        raise HTTPException(404, "Emergency profile not found")
    return _profile_response(profile)


@router.put(
    "/patients/{health_id}/emergency-profile",
    response_model=EmergencyProfileResponse,
)
async def save_emergency_profile(
    health_id: str,
    request: EmergencyProfileRequest,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    await _owned_patient(health_id, user, session)
    profile = await EmergencyService(session).save_emergency_profile(health_id, request)
    await session.commit()
    return _profile_response(profile)


@router.post(
    "/patients/{health_id}/break-glass",
    response_model=BreakGlassResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invoke_break_glass(
    health_id: str,
    request: BreakGlassRequest,
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
    try:
        event, token, expires_at = await EmergencyService(session).invoke_break_glass(
            health_id,
            str(user.get("sub", "")),
            request.reason,
            request.tier.value,
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(404, str(exc)) from exc
    return BreakGlassResponse(
        event_id=event.id,
        health_id=health_id,
        authorization_token=token,
        expires_at=expires_at,
    )


@router.get(
    "/patients/{health_id}/notifications",
    response_model=list[PatientNotificationResponse],
)
async def patient_notifications(
    health_id: str,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
):
    await _owned_patient(health_id, user, session)
    return await EmergencyService(session).get_notifications(health_id)
