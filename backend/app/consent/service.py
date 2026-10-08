from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent.models import Consent
from app.consent.schemas import ConsentCreateRequest, ConsentStatus
from app.identity.models import PatientIdentity
from app.provider_trust.models import Provider


class ConsentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_consent(self, request: ConsentCreateRequest) -> Consent:
        if request.grantee_type == "PROVIDER":
            provider = await self.session.scalar(
                select(Provider).where(
                    Provider.external_id == request.grantee_id,
                    Provider.trust_status == "ACTIVE",
                )
            )
            if provider is None:
                raise ValueError("Doctor HealthNet Provider ID is not valid or active")

        if request.valid_until and request.valid_until <= request.valid_from:
            raise ValueError("valid_until must be after valid_from")

        x = Consent(
            health_id=request.health_id,
            grantee_type=request.grantee_type,
            grantee_id=request.grantee_id,
            purpose=request.purpose,
            scopes=",".join(sorted(set(request.scopes))),
            status=ConsentStatus.ACTIVE.value,
            valid_from=request.valid_from,
            valid_until=request.valid_until,
            reason=request.reason,
        )
        self.session.add(x)
        await self.session.flush()
        return x

    async def get_consent(self, consent_id: UUID):
        return await self.session.get(Consent, consent_id)

    async def revoke_consent(self, consent_id: UUID) -> Consent | None:
        x = await self.get_consent(consent_id)
        if x is None:
            return None
        x.status = ConsentStatus.REVOKED.value
        x.revoked_at = datetime.now(UTC)
        await self.session.flush()
        return x

    async def check_consent(
        self,
        health_id: str,
        grantee_id: str,
        purpose: str,
        scope: str,
        at: datetime | None = None,
    ) -> bool:
        moment = at or datetime.now(UTC)
        result = await self.session.execute(
            select(Consent).where(
                Consent.health_id == health_id,
                Consent.grantee_id == grantee_id,
                Consent.purpose == purpose,
                Consent.status == ConsentStatus.ACTIVE.value,
                Consent.valid_from <= moment,
                (Consent.valid_until.is_(None) | (Consent.valid_until >= moment)),
            )
        )
        return any(
            scope in (x.scopes.split(",") if x.scopes else [])
            for x in result.scalars()
        )

    async def get_patient_consents(self, health_id: str) -> list[Consent]:
        result = await self.session.execute(
            select(Consent)
            .where(Consent.health_id == health_id)
            .order_by(Consent.created_at.desc())
        )
        return list(result.scalars())

    async def get_authorized_patients(
        self, provider_subject: str
    ) -> list[tuple[Consent, PatientIdentity]]:
        moment = datetime.now(UTC)
        result = await self.session.execute(
            select(Consent, PatientIdentity)
            .join(
                Provider,
                Provider.external_id == Consent.grantee_id,
            )
            .join(
                PatientIdentity,
                PatientIdentity.display_health_id == Consent.health_id,
            )
            .where(
                Provider.keycloak_subject == provider_subject,
                Provider.trust_status == "ACTIVE",
                Consent.grantee_type == "PROVIDER",
                Consent.status == ConsentStatus.ACTIVE.value,
                Consent.valid_from <= moment,
                (Consent.valid_until.is_(None) | (Consent.valid_until >= moment)),
                PatientIdentity.status == "ACTIVE",
            )
            .order_by(PatientIdentity.family_name, PatientIdentity.given_name)
        )
        return list(result.all())
