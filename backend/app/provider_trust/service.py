from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.provider_trust.models import Organization, Provider, PractitionerRole
from app.provider_trust.schemas import (
    OrganizationCreate,
    ProviderCreate,
    PractitionerRoleCreate,
    TrustStatus,
)


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
