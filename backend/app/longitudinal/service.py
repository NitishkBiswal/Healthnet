from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.fhir.client import FHIRClient
from app.longitudinal.schemas import DataCompleteness, LongitudinalViewRequest, LongitudinalViewResponse
from app.record_locator.models import RecordLocator
from app.repository.models import Repository, RepositoryStatus

class LongitudinalViewService:
    """Query-time federation. NEVER permanently copies records into a central database."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def build_longitudinal_view(self, request: LongitudinalViewRequest) -> LongitudinalViewResponse:
        locators = list(
            (
                await self.session.scalars(
                    select(RecordLocator)
                    .where(
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
