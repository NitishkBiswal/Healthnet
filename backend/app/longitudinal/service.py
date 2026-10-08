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
from app.provider_trust.models import Provider
from app.record_locator.models import RecordLocator
from app.repository.models import Repository, RepositoryStatus


class LongitudinalAccessDenied(ValueError):
    """Raised when a Doctor request fails an authorization gate."""


class LongitudinalViewService:
    """Retrieves a patient's record from exactly one authoritative repository."""

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

        consent_allowed = await ConsentService(self.session).check_consent(
            request.health_id,
            provider.external_id,
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

        locator = await self.session.scalar(
            select(RecordLocator)
            .where(
                RecordLocator.health_id == request.health_id,
                RecordLocator.status == "ACTIVE",
            )
            .order_by(RecordLocator.created_at.desc())
        )

        if locator is None:
            return LongitudinalViewResponse(
                health_id=request.health_id,
                completeness=DataCompleteness.UNAVAILABLE,
                current_repository=None,
                records=[],
                repositories_checked=0,
                repositories_available=0,
                errors=["No current repository is assigned to this patient"],
            )

        repository = await self.session.get(Repository, locator.repository_id)
        if repository is None:
            return LongitudinalViewResponse(
                health_id=request.health_id,
                completeness=DataCompleteness.UNAVAILABLE,
                current_repository=None,
                records=[],
                repositories_checked=1,
                repositories_available=0,
                errors=["The patient's current repository is not registered"],
            )

        current_repository = {
            "code": repository.code,
            "name": repository.name,
            "jurisdiction": repository.jurisdiction,
            "endpoint": locator.endpoint or repository.base_url,
        }

        if repository.status == RepositoryStatus.OFFLINE:
            return LongitudinalViewResponse(
                health_id=request.health_id,
                current_repository=current_repository,
                completeness=DataCompleteness.UNAVAILABLE,
                records=[],
                repositories_checked=1,
                repositories_available=0,
                errors=[f"Current repository {repository.code} is offline"],
            )

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
            return LongitudinalViewResponse(
                health_id=request.health_id,
                current_repository=current_repository,
                completeness=DataCompleteness.UNAVAILABLE,
                records=[],
                repositories_checked=1,
                repositories_available=1,
                errors=[f"{repository.code}: {policy_reason}"],
            )

        records: list[dict[str, Any]] = []
        errors: list[str] = []
        resource_types = [
            value.strip()
            for value in locator.resource_types.split(",")
            if value.strip()
        ] or ["Observation"]

        client = FHIRClient(locator.endpoint or repository.base_url)
        for resource_type in resource_types:
            try:
                resources: list[dict] = []
                if resource_type == "Patient":
                    bundle = await client.search(
                        "Patient",
                        {"identifier": f"urn:healthnet:health-id|{request.health_id}"},
                    )
                    for entry in bundle.get("entry", []):
                        if not isinstance(entry, dict):
                            continue
                        patient_resource = entry.get("resource")
                        if isinstance(patient_resource, dict):
                            resources.append(patient_resource)
                    if not resources:
                        try:
                            resources.append(
                                await client.get_resource("Patient", request.health_id)
                            )
                        except Exception as exc:
                            errors.append(
                                f"{repository.code}/Patient: {type(exc).__name__}"
                            )
                else:
                    bundle = await client.search(
                        resource_type,
                        {"patient": request.health_id},
                    )
                    for entry in bundle.get("entry", []):
                        if not isinstance(entry, dict):
                            continue
                        clinical_resource = entry.get("resource")
                        if isinstance(clinical_resource, dict):
                            resources.append(clinical_resource)

                for resource in resources:
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

        completeness = DataCompleteness.PARTIAL if errors else DataCompleteness.COMPLETE
        return LongitudinalViewResponse(
            health_id=request.health_id,
            current_repository=current_repository,
            completeness=completeness,
            records=records,
            repositories_checked=1,
            repositories_available=1,
            errors=errors,
        )

    async def aggregate_results(self) -> list[dict[str, Any]]:
        return []
