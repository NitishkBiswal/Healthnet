from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.consent.service import ConsentService
from app.emergency.service import EmergencyService
from app.fhir.client import FHIRClient
from app.jurisdiction_policy.schemas import PolicyEvaluationRequest
from app.jurisdiction_policy.service import JurisdictionPolicyService
from app.longitudinal.schemas import (
    DataCompleteness,
    LongitudinalViewRequest,
    LongitudinalViewResponse,
)
from app.provider_trust.models import Provider
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
        break_glass_token: str | None = None,
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

        # Organization/PractitionerRole trust is intentionally deferred for the
        # current MVP. Provider trust + patient consent are sufficient for now.
        # This can be restored when organization onboarding is implemented.

        consent_allowed = await ConsentService(self.session).check_consent(
            request.health_id,
            provider.external_id,
            request.purpose,
            request.scope,
        )
        if (
            not consent_allowed
            and request.purpose == "EMERGENCY"
            and await EmergencyService(self.session).validate_break_glass(
                request.health_id, str(subject), break_glass_token
            )
        ):
            consent_allowed = True
        if not consent_allowed:
            raise LongitudinalAccessDenied(
                "No active patient consent for this purpose and scope"
            )

        return provider

    async def build_longitudinal_view(
        self,
        request: LongitudinalViewRequest,
        user: dict[str, Any],
        break_glass_token: str | None = None,
    ) -> LongitudinalViewResponse:
        provider = await self._authorize_doctor(request, user, break_glass_token)

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
            if request.resource_types:
                requested = set(request.resource_types)
                resource_types = [
                    resource_type
                    for resource_type in resource_types
                    if resource_type in requested
                ]
            client = FHIRClient(locator.endpoint or repository.base_url)

            for resource_type in resource_types:
                try:
                    search_params: dict[str, Any] = {
                        "subject": f"Patient/{request.health_id}"
                    }
                    date_filters = []
                    if request.from_date:
                        date_filters.append(f"ge{request.from_date.isoformat()}")
                    if request.to_date:
                        date_filters.append(f"le{request.to_date.isoformat()}")
                    if date_filters:
                        search_params["date"] = date_filters
                    bundle = await client.search(
                        resource_type,
                        search_params,
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

        await AuditService(self.session).log_event(
            AuditEventCreate(
                event_type=AuditEventType.RETRIEVAL,
                health_id=request.health_id,
                actor_id=str(user.get("sub", "unknown")),
                action="longitudinal patient records retrieved",
                payload={
                    "purpose": request.purpose,
                    "scope": request.scope,
                    "break_glass_token_provided": bool(break_glass_token),
                    "repositories_checked": repositories_checked,
                },
            )
        )
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
