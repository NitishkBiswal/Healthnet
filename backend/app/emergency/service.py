import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.core.config import settings
from app.emergency.models import (
    BreakGlassEvent,
    BreakGlassGrant,
    EmergencyHealthProfile,
    PatientNotification,
)
from app.emergency.schemas import EmergencyProfileRequest
from app.identity.models import PatientIdentity


def _decode_list(value: str) -> list[str]:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return [item for item in value.split(",") if item]
    return decoded if isinstance(decoded, list) else []


class EmergencyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_emergency_profile(self, health_id: str) -> EmergencyHealthProfile | None:
        return await self.session.scalar(
            select(EmergencyHealthProfile).where(
                EmergencyHealthProfile.health_id == health_id
            )
        )

    async def save_emergency_profile(
        self, health_id: str, request: EmergencyProfileRequest
    ) -> EmergencyHealthProfile:
        profile = await self.get_emergency_profile(health_id)
        if profile is None:
            profile = EmergencyHealthProfile(health_id=health_id)
            self.session.add(profile)
        profile.blood_group = request.blood_group
        profile.allergies = json.dumps(request.allergies)
        profile.medications = json.dumps(request.medications)
        profile.conditions = json.dumps(request.conditions)
        profile.emergency_contacts = json.dumps(request.emergency_contacts)
        await self.session.flush()
        return profile

    async def invoke_break_glass(
        self,
        health_id: str,
        actor_id: str,
        reason: str,
        tier: str,
    ) -> tuple[BreakGlassEvent, str, datetime]:
        patient = await self.session.scalar(
            select(PatientIdentity).where(
                PatientIdentity.display_health_id == health_id
            )
        )
        if patient is None:
            raise ValueError("Patient not found")

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=settings.BREAK_GLASS_TTL_MINUTES)
        raw_token = secrets.token_urlsafe(32)
        event = BreakGlassEvent(
            health_id=health_id,
            actor_id=actor_id,
            reason=reason,
        )
        self.session.add(event)
        await self.session.flush()
        self.session.add(
            BreakGlassGrant(
                event_id=event.id,
                health_id=health_id,
                actor_id=actor_id,
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_at=expires_at,
            )
        )
        self.session.add(
            PatientNotification(
                patient_subject=patient.owner_subject or "",
                health_id=health_id,
                event_type="BREAK_GLASS",
                message=(
                    f"Emergency access to your HealthNet record was invoked by "
                    f"a healthcare provider. Reason: {reason}"
                ),
            )
        )
        await AuditService(self.session).log_event(
            AuditEventCreate(
                event_type=AuditEventType.BREAK_GLASS,
                health_id=health_id,
                actor_id=actor_id,
                action="temporary emergency record access granted",
                payload={"event_id": str(event.id), "tier": tier, "expires_at": expires_at.isoformat()},
            )
        )
        await self.session.flush()
        return event, raw_token, expires_at

    async def validate_break_glass(
        self, health_id: str, actor_id: str, token: str | None
    ) -> bool:
        if not token:
            return False
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        grant = await self.session.scalar(
            select(BreakGlassGrant).where(
                BreakGlassGrant.health_id == health_id,
                BreakGlassGrant.actor_id == actor_id,
                BreakGlassGrant.token_hash == token_hash,
                BreakGlassGrant.expires_at > datetime.now(UTC),
                BreakGlassGrant.revoked_at.is_(None),
            )
        )
        return grant is not None

    async def get_notifications(self, health_id: str) -> list[PatientNotification]:
        result = await self.session.scalars(
            select(PatientNotification)
            .where(PatientNotification.health_id == health_id)
            .order_by(PatientNotification.created_at.desc())
            .limit(100)
        )
        return list(result.all())

    @staticmethod
    def profile_lists(profile: EmergencyHealthProfile) -> dict[str, list[str]]:
        return {
            "allergies": _decode_list(profile.allergies),
            "medications": _decode_list(profile.medications),
            "conditions": _decode_list(profile.conditions),
            "emergency_contacts": _decode_list(profile.emergency_contacts),
        }
