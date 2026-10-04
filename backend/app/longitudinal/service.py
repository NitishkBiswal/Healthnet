from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent.service import ConsentService
from app.fhir.client import FHIRClient
from app.jurisdiction_policy.schemas import PolicyEvaluationRequest
from app.jurisdiction_policy.service import JurisdictionPolicyService
from app.longitudinal.schemas import (
    DataCompleteness,
    LongitudinalViewRequest,
    LongitudinalViewResponse,
)
from app.provider_trust.models import Organization, PractitionerRole, Provider
from app.record_locator.models import RecordLocator
from app.repository.models import Repository, RepositoryStatus


class LongitudinalAccessDenied(ValueError):
    """Raised when a Doctor request fails an authorization gate."""


class LongitudinalViewService:
    """Query-time federation. NEVER permanently copies records into a central database."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _authorize_doctor(
        self,
        request: LongitudinalViewRequest,
        user: dict[str, Any],
    ) -> Provider:
        roles = set(user.get("roles", []))
        if "PROVIDER" not in roles:
            raise LongitudinalAccessDenied(
                "Provider role is required for longitudinal patient access"
            )

        subject = user.get("sub")
        if not subject:
            raise LongitudinalAccessDenied("Authenticated principal has no subject")

        provider = await self.session.scalar(
            select(Provider).where(
                Provider.keycloak_subject == subject,
                Provider.trust_status == "ACTIVE",
            )
        )
        if provider is None:
            raise LongitudinalAccessDenied(
                "No active trusted HealthNet provider is linked to this principal"
            )

        active_role = await self.session.scalar(
            select(PractitionerRole)
            .join(Organization, PractitionerRole.organization_id == Organization.id)
            .where(
                PractitionerRole.provider_id == provider.id,
                PractitionerRole.active.is_(True),
                Organization.trust_status == "ACTIVE",
            )
        )
        if active_role is None:
            raise LongitudinalAccessDenied(
                "Provider has no active role in a trusted organization"
            )

        consent_allowed = await ConsentService(self.session).check_consent(
            request.health_id,
            subject,
            request.purpose,
            request.scope,
        )
        if not consent_allowed:
            raise LongitudinalAccessDenied(
                "No active patient consent for this purpose and scope"
            )

        return provider

    async def build_longitudinal_view(
        self,
        request: LongitudinalViewRequest,
        user: dict[str, Any],
    ) -> LongitudinalViewResponse:
        provider = await self._authorize_doctor(request, user)

        locators = list(
            (
                await self.session.scalars(
                    select(RecordLocator).where(
                        RecordLocator.health_id == request.health_id,
                        RecordLocator.status == "ACTIVE",
                    )
                )
            ).all()
        )
        repositories_checked = len(locators)
        records: list[dict[str, Any]] = []
        errors: list[str] = []
        repositories_available = 0

        for locator in locators:
            repository = await self.session.get(Repository, locator.repository_id)
            if repository is None:
                errors.append(f"Repository {locator.repository_id} not found")
                continue
            if repository.status == RepositoryStatus.OFFLINE:
                errors.append(f"Repository {repository.code} is offline")
                continue

            policy_allowed, policy_reason, _ = (
                await JurisdictionPolicyService(self.session).evaluate_policy(
                    PolicyEvaluationRequest(
                        source_jurisdiction=repository.jurisdiction,
                        destination_jurisdiction=provider.jurisdiction,
                        purpose=request.purpose,
                        scope=request.scope,
                    )
                )
            )
            if not policy_allowed:
                errors.append(f"{repository.code}: {policy_reason}")
                continue

            repositories_available += 1
            resource_types = [
                value.strip()
                for value in locator.resource_types.split(",")
                if value.strip()
            ] or ["Observation"]
            client = FHIRClient(locator.endpoint or repository.base_url)

            for resource_type in resource_types:
                try:
                    bundle = await client.search(
                        resource_type,
                        {"patient": request.health_id},
                    )
                    for entry in bundle.get("entry", []):
                        resource = entry.get("resource")
                        if isinstance(resource, dict):
                            records.append(
                                {
                                    "repository": repository.code,
                                    "resource_type": resource_type,
                                    "resource": resource,
                                }
                            )
                except Exception as exc:
                    errors.append(
                        f"{repository.code}/{resource_type}: {type(exc).__name__}"
                    )

        if repositories_checked == 0 or repositories_available == 0:
            completeness = DataCompleteness.UNAVAILABLE
        elif errors:
            completeness = DataCompleteness.PARTIAL
        else:
            completeness = DataCompleteness.COMPLETE

        return LongitudinalViewResponse(
            health_id=request.health_id,
            completeness=completeness,
            records=records,
            repositories_checked=repositories_checked,
            repositories_available=repositories_available,
            errors=errors,
        )

    async def aggregate_results(self) -> list[dict[str, Any]]:
        return []
