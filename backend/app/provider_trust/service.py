from datetime import UTC, datetime
from uuid import UUID
import asyncio
import logging
import json
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.provider_trust.models import Organization, Provider, PractitionerRole, ProviderJurisdictionRequest
from app.core.config import settings
from app.provider_trust.schemas import (
    OrganizationCreate,
    ProviderCreate,
    PractitionerRoleCreate,
    TrustStatus,
    ProviderOnboardRequest,
    ProviderJurisdictionRequestCreate,
)

logger = logging.getLogger(__name__)


class ProviderTrustService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_organization(self, request: OrganizationCreate) -> Organization:
        if await self.session.scalar(
            select(Organization).where(Organization.external_id == request.external_id)
        ):
            raise ValueError("Organization external_id already exists")
        x = Organization(
            **request.model_dump(),
            trust_status=TrustStatus.ACTIVE.value,
        )
        self.session.add(x)
        await self.session.flush()
        return x

    async def get_organization(self, org_id: UUID):
        return await self.session.get(Organization, org_id)

    async def register_provider(self, request: ProviderCreate) -> Provider:
        if await self.session.scalar(
            select(Provider).where(Provider.license_number == request.license_number)
        ):
            raise ValueError("License number already exists")
        if await self.session.scalar(
            select(Provider).where(Provider.external_id == request.external_id)
        ):
            raise ValueError("Provider HealthNet ID already exists")
        if request.keycloak_subject and await self.session.scalar(
            select(Provider).where(Provider.keycloak_subject == request.keycloak_subject)
        ):
            raise ValueError("Keycloak subject is already linked to another provider")

        x = Provider(
            **request.model_dump(),
            trust_status=TrustStatus.ACTIVE.value,
        )
        self.session.add(x)
        await self.session.flush()
        return x

    async def onboard_provider(self, request: ProviderOnboardRequest) -> tuple[Provider, str]:
        if await self.session.scalar(select(Provider).where(Provider.license_number == request.license_number)):
            raise ValueError("License number already exists")
        token = await asyncio.to_thread(self._keycloak_admin_token)
        subject = ""
        try:
            subject = await asyncio.to_thread(self._create_keycloak_doctor, token, request)
            result = await self.session.execute(select(Provider.external_id))
            numbers = []
            for value in result.scalars():
                if value.startswith("PRV-IN-"):
                    try:
                        numbers.append(int(value.rsplit("-", 1)[1]))
                    except ValueError:
                        pass
            provider_id = f"PRV-IN-{(max(numbers, default=0) + 1):06d}"
            provider = Provider(external_id=provider_id, given_name=request.given_name,
                family_name=request.family_name, license_number=request.license_number,
                jurisdiction=request.jurisdiction, keycloak_subject=subject,
                trust_status=TrustStatus.ACTIVE.value)
            self.session.add(provider)
            await self.session.flush()
            return provider, request.username
        except Exception:
            await asyncio.to_thread(self._delete_keycloak_user, token, subject)
            raise

    def _keycloak_admin_token(self) -> str:
        data = urllib.parse.urlencode({"grant_type":"password","client_id":"admin-cli",
            "username":settings.KEYCLOAK_ADMIN_USERNAME,"password":settings.KEYCLOAK_ADMIN_PASSWORD}).encode()
        req = urllib.request.Request(f"{settings.KEYCLOAK_URL.rstrip('/')}/realms/master/protocol/openid-connect/token",
            data=data, headers={"Content-Type":"application/x-www-form-urlencoded"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())["access_token"]

    def _create_keycloak_doctor(self, token: str, request: ProviderOnboardRequest) -> str:
        payload=json.dumps({"username":request.username,"email":request.email,"firstName":request.given_name,
            "lastName":request.family_name,"enabled":True,"emailVerified":False,
            "credentials":[{"type":"password","value":request.initial_password,"temporary":False}]}).encode()
        req=urllib.request.Request(f"{settings.KEYCLOAK_URL.rstrip('/')}/admin/realms/{settings.KEYCLOAK_REALM}/users",
            data=payload,headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=10) as response: location=response.headers.get("Location","")
        except urllib.error.HTTPError as exc:
            if exc.code==409: raise ValueError("Doctor username or email already exists") from exc
            raise ValueError(f"Keycloak user creation failed ({exc.code})") from exc
        subject=location.rstrip("/").split("/")[-1]
        if not subject: raise ValueError("Keycloak did not return the new doctor user ID")
        role_req=urllib.request.Request(f"{settings.KEYCLOAK_URL.rstrip('/')}/admin/realms/{settings.KEYCLOAK_REALM}/roles/provider",
            headers={"Authorization":f"Bearer {token}"},method="GET")
        with urllib.request.urlopen(role_req,timeout=10) as response: role=json.loads(response.read())
        mapping=urllib.request.Request(f"{settings.KEYCLOAK_URL.rstrip('/')}/admin/realms/{settings.KEYCLOAK_REALM}/users/{subject}/role-mappings/realm",
            data=json.dumps([role]).encode(),headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},method="POST")
        with urllib.request.urlopen(mapping,timeout=10): pass
        return subject

    def _delete_keycloak_user(self, token: str, subject: str) -> None:
        if not subject: return
        req=urllib.request.Request(f"{settings.KEYCLOAK_URL.rstrip('/')}/admin/realms/{settings.KEYCLOAK_REALM}/users/{subject}",
            headers={"Authorization":f"Bearer {token}"},method="DELETE")
        try:
            urllib.request.urlopen(req, timeout=10).close()
        except Exception:
            logger.warning("Failed to delete partially created Keycloak user %s", subject, exc_info=True)

    async def list_providers(self) -> list[Provider]:
        result = await self.session.execute(
            select(Provider).order_by(Provider.family_name, Provider.given_name)
        )
        return list(result.scalars())

    async def get_provider(self, provider_id: UUID):
        return await self.session.get(Provider, provider_id)

    async def set_organization_status(
        self, org_id: UUID, status: TrustStatus
    ):
        x = await self.get_organization(org_id)
        if x is None:
            raise ValueError("Organization not found")
        x.trust_status = status.value
        await self.session.flush()
        return x

    async def set_provider_status(
        self, provider_id: UUID, status: TrustStatus
    ):
        x = await self.get_provider(provider_id)
        if x is None:
            raise ValueError("Provider not found")
        x.trust_status = status.value
        await self.session.flush()
        return x

    async def create_jurisdiction_request(
        self, provider_subject: str, request: ProviderJurisdictionRequestCreate
    ) -> ProviderJurisdictionRequest:
        provider = await self.session.scalar(
            select(Provider).where(Provider.keycloak_subject == provider_subject)
        )
        if provider is None:
            raise ValueError("Your account is not linked to a HealthNet provider")
        if provider.trust_status != TrustStatus.ACTIVE.value:
            raise ValueError("Only active providers can request a jurisdiction transfer")
        requested = request.requested_jurisdiction.strip().upper()
        if requested == provider.jurisdiction.upper():
            raise ValueError("You are already registered in this jurisdiction")
        pending = await self.session.scalar(
            select(ProviderJurisdictionRequest).where(
                ProviderJurisdictionRequest.provider_id == provider.id,
                ProviderJurisdictionRequest.status == "PENDING",
            )
        )
        if pending:
            raise ValueError("You already have a pending jurisdiction transfer request")
        item = ProviderJurisdictionRequest(
            provider_id=provider.id,
            current_jurisdiction=provider.jurisdiction,
            requested_jurisdiction=requested,
            reason=request.reason.strip(),
            status="PENDING",
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_my_jurisdiction_requests(self, provider_subject: str):
        provider = await self.session.scalar(
            select(Provider).where(Provider.keycloak_subject == provider_subject)
        )
        if provider is None:
            raise ValueError("Your account is not linked to a HealthNet provider")
        result = await self.session.execute(
            select(ProviderJurisdictionRequest)
            .where(ProviderJurisdictionRequest.provider_id == provider.id)
            .order_by(ProviderJurisdictionRequest.created_at.desc())
        )
        return list(result.scalars())

    async def list_jurisdiction_requests(self):
        result = await self.session.execute(
            select(ProviderJurisdictionRequest, Provider)
            .join(Provider, Provider.id == ProviderJurisdictionRequest.provider_id)
            .order_by(ProviderJurisdictionRequest.created_at.desc())
        )
        return [
            {
                **{column.name: getattr(item, column.name) for column in ProviderJurisdictionRequest.__table__.columns},
                "provider_external_id": provider.external_id,
                "provider_name": f"{provider.given_name} {provider.family_name}",
            }
            for item, provider in result.all()
        ]

    async def review_jurisdiction_request(
        self, request_id: UUID, reviewer_subject: str, decision: str, reviewer_note: str | None
    ):
        item = await self.session.scalar(
            select(ProviderJurisdictionRequest)
            .where(ProviderJurisdictionRequest.id == request_id)
            .with_for_update()
        )
        if item is None:
            raise ValueError("Jurisdiction transfer request not found")
        if item.status != "PENDING":
            raise ValueError("This request has already been reviewed")
        provider = await self.session.get(Provider, item.provider_id)
        if provider is None:
            raise ValueError("Provider not found")
        if decision == "APPROVE":
            provider.jurisdiction = item.requested_jurisdiction
            item.status = "APPROVED"
        else:
            note = (reviewer_note or "").strip()
            if len(note) < 10:
                raise ValueError("A rejection reason of at least 10 characters is required")
            item.status = "REJECTED"
            item.reviewer_note = note
        item.reviewer_subject = reviewer_subject
        item.reviewed_at = datetime.now(UTC)
        await self.session.flush()
        return item

    async def assign_role(self, request: PractitionerRoleCreate) -> PractitionerRole:
        if (
            await self.get_provider(request.provider_id) is None
            or await self.get_organization(request.organization_id) is None
        ):
            raise ValueError("Provider or organization not found")
        x = PractitionerRole(**request.model_dump(), active=True)
        self.session.add(x)
        await self.session.flush()
        return x
