from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent
from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.consent.service import ConsentService
from app.core.database import get_db
from app.emergency.models import BreakGlassEvent
from app.emergency.schemas import (
    BreakGlassRequest,
    BreakGlassSummaryResponse,
    EmergencyProfileResponse,
)
from app.emergency.service import EmergencyService
from app.identity.service import IdentityService
from app.provider_trust.models import Provider
from app.security.dependencies import require_role
from app.security.rbac import Role

router = APIRouter(tags=["Emergency"])


# Use the actual FastAPI dependency, not a wrapper that returns a dependency function.
require_provider = require_role(Role.PROVIDER)
BREAK_GLASS_VALIDITY = timedelta(minutes=15)


def response(profile):
    return EmergencyProfileResponse(
        health_id=profile.health_id,
        blood_group=profile.blood_group,
        allergies=[v for v in (profile.allergies or "").split(",") if v.strip()],
        medications=[v for v in (profile.medications or "").split(",") if v.strip()],
        conditions=[v for v in (profile.conditions or "").split(",") if v.strip()],
        emergency_contacts=[v for v in (profile.emergency_contacts or "").split(",") if v.strip()],
    )


async def _active_provider(user: dict, session: AsyncSession) -> Provider:
    if "PROVIDER" not in set(user.get("roles", [])) or not user.get("sub"):
        raise HTTPException(403, "An authenticated provider account is required")
    provider = await session.scalar(
        select(Provider).where(
            Provider.keycloak_subject == str(user["sub"]),
            Provider.trust_status == "ACTIVE",
        )
    )
    if provider is None:
        raise HTTPException(403, "No active trusted provider is linked to this account")
    return provider


@router.get("/patients/{health_id}/emergency-profile", response_model=EmergencyProfileResponse)
async def get_emergency_profile(
    health_id: str,
    user: dict = Depends(require_provider),
    purpose: str = Query(default="TREATMENT", min_length=1, max_length=64),
    scope: str = Query(default="clinical", min_length=1, max_length=64),
    session: AsyncSession = Depends(get_db),
):
    provider = await _active_provider(user, session)
    consent_service = ConsentService(session)
    consent_allowed = await consent_service.check_consent(
        health_id, provider.external_id, purpose, scope
    )
    if not consent_allowed:
        consent_allowed = await consent_service.check_consent(
            health_id, provider.external_id, purpose, "emergency"
        )

    if not consent_allowed:
        raise HTTPException(
            403,
            "Active patient consent is required for the standard emergency profile. Use the separately audited break-glass summary for a genuine emergency.",
        )

    profile = await EmergencyService(session).get_emergency_profile(health_id)
    if profile is None:
        raise HTTPException(404, "Emergency profile not found")

    await AuditService(session).log_event(
        AuditEventCreate(
            event_type=AuditEventType.ACCESS,
            health_id=health_id,
            actor_id=str(user["sub"]),
            action="EMERGENCY_PROFILE_VIEWED",
            payload={
                "provider_id": provider.external_id,
                "access_method": "PATIENT_CONSENT",
                "purpose": purpose,
                "scope": scope,
            },
        )
    )
    await session.commit()
    return response(profile)


@router.get(
    "/patients/{health_id}/break-glass-summary",
    response_model=BreakGlassSummaryResponse,
)
async def get_break_glass_summary(
    health_id: str,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    """Return only emergency-relevant chronic conditions after a one-time grant."""
    provider = await _active_provider(user, session)
    cutoff = datetime.now(UTC) - BREAK_GLASS_VALIDITY
    event = await session.scalar(
        select(BreakGlassEvent)
        .where(
            BreakGlassEvent.health_id == health_id,
            BreakGlassEvent.actor_id == str(user["sub"]),
            BreakGlassEvent.invoked_at >= cutoff,
        )
        .order_by(BreakGlassEvent.invoked_at.desc())
        .limit(1)
        .with_for_update()
    )
    if event is None:
        raise HTTPException(403, "A valid emergency authorization is required before viewing this summary")

    already_used = await session.scalar(
        select(AuditEvent.id).where(
            AuditEvent.action == "BREAK_GLASS_CHRONIC_SUMMARY_VIEWED",
            AuditEvent.payload.contains(str(event.id)),
        ).limit(1)
    )
    if already_used is not None:
        raise HTTPException(403, "This emergency authorization has already been used")

    profile = await EmergencyService(session).get_emergency_profile(health_id)
    chronic_conditions = [
        value.strip() for value in (profile.conditions if profile else "").split(",")
        if value.strip()
    ]
    if not chronic_conditions:
        raise HTTPException(404, "No emergency-relevant chronic conditions are recorded for this patient")

    expires_at = event.invoked_at + BREAK_GLASS_VALIDITY
    await AuditService(session).log_event(
        AuditEventCreate(
            event_type=AuditEventType.ACCESS,
            health_id=health_id,
            actor_id=str(user["sub"]),
            action="BREAK_GLASS_CHRONIC_SUMMARY_VIEWED",
            payload={
                "provider_id": provider.external_id,
                "provider_jurisdiction": provider.jurisdiction,
                "break_glass_event_id": str(event.id),
                "access_scope": "CHRONIC_CONDITIONS_ONLY",
                "condition_count": len(chronic_conditions),
                "access_expires_at": expires_at.isoformat(),
            },
        )
    )
    await session.commit()
    return BreakGlassSummaryResponse(
        health_id=health_id,
        chronic_conditions=chronic_conditions,
        access_expires_at=expires_at.isoformat(),
    )


@router.post("/patients/{health_id}/break-glass")
async def invoke_break_glass(
    health_id: str,
    request: BreakGlassRequest,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    provider = await _active_provider(user, session)
    if request.emergency_declaration is not True:
        raise HTTPException(400, "You must confirm that this is a genuine emergency")
    patient = await IdentityService(session).get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(404, "Patient Health ID was not found")
    profile = await EmergencyService(session).get_emergency_profile(health_id)
    if profile is None or not any(value.strip() for value in (profile.conditions or "").split(",")):
        raise HTTPException(404, "No emergency-relevant chronic conditions are recorded for this patient; break-glass access is not available")
    event = await EmergencyService(session).invoke_break_glass(
        health_id, str(user["sub"]), request.reason
    )
    await AuditService(session).log_event(
        AuditEventCreate(
            event_type=AuditEventType.BREAK_GLASS,
            health_id=health_id,
            actor_id=str(user["sub"]),
            action="BREAK_GLASS_INVOKED",
            payload={
                "reason": request.reason,
                "tier": request.tier.value,
                "provider_id": provider.external_id,
                "provider_jurisdiction": provider.jurisdiction,
                "access_scope": "CHRONIC_CONDITIONS_ONLY",
                "valid_for_minutes": int(BREAK_GLASS_VALIDITY.total_seconds() / 60),
            },
        )
    )
    await session.commit()
    return {
        "event_id": event.id,
        "health_id": health_id,
        "tier": request.tier,
        "status": "BREAK_GLASS_GRANTED",
        "valid_for_minutes": int(BREAK_GLASS_VALIDITY.total_seconds() / 60),
        "message": "Restricted emergency-profile access authorized. This does not grant access to the longitudinal medical record.",
    }
