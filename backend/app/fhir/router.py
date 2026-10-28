from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.consent.service import ConsentService
from app.core.database import get_db
from app.fhir.client import FHIRClient
from app.fhir.schemas import FHIRResource
from app.provider_trust.models import Provider
from app.repository.models import EHRCustody, Repository, RepositoryStatus
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role

router = APIRouter(tags=["FHIR"])
require_provider = require_role(Role.PROVIDER)
SUPPORTED_RESOURCE_TYPES = {
    "AllergyIntolerance",
    "Condition",
    "DiagnosticReport",
    "Encounter",
    "Immunization",
    "MedicationRequest",
    "Observation",
    "Procedure",
}
REQUIRED_RESOURCE_FIELDS = {
    "AllergyIntolerance": ("patient",),
    "Condition": ("code",),
    "DiagnosticReport": ("status", "code"),
    "Encounter": ("status", "class"),
    "Immunization": ("status", "vaccineCode", "occurrenceDateTime", "patient"),
    "MedicationRequest": ("status", "intent", "medicationCodeableConcept", "subject"),
    "Observation": ("status", "code",),
    "Procedure": ("status", "code",),
}


def _validate_supported_resource(resource: FHIRResource) -> None:
    payload = resource.model_dump(exclude_none=True)
    resource_type = payload.get("resourceType")
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise ValueError(f"FHIR resource type {resource_type} is not supported")
    missing = [field for field in REQUIRED_RESOURCE_FIELDS[resource_type] if field not in payload]
    if missing:
        raise ValueError(f"FHIR resource is missing required field(s): {', '.join(missing)}")


def _health_id(resource: FHIRResource) -> str:
    subject = resource.model_dump(exclude_none=True).get("subject")
    reference = subject.get("reference") if isinstance(subject, dict) else None
    if not isinstance(reference, str) or not reference.startswith("Patient/"):
        raise ValueError("FHIR resource subject must reference Patient/<Health ID>")
    return reference.removeprefix("Patient/").strip()


async def _active_repository(session: AsyncSession, health_id: str) -> Repository:
    custody = await session.scalar(
        select(EHRCustody)
        .where(EHRCustody.health_id == health_id, EHRCustody.custody_end.is_(None))
        .order_by(EHRCustody.custody_start.desc())
    )
    if custody is None:
        raise ValueError("No active repository is configured for this patient")
    repository = await session.get(Repository, custody.repository_id)
    if repository is None or repository.status == RepositoryStatus.OFFLINE:
        raise ValueError("The active repository is unavailable")
    return repository


@router.get("/metadata")
async def metadata(_: dict = Depends(get_current_user)):
    try:
        return await FHIRClient().get_metadata()
    except Exception as exc:
        raise HTTPException(502, "FHIR repository unavailable") from exc


@router.get("/{resource_type}/{resource_id}")
async def get_resource(resource_type: str, resource_id: str, _: dict = Depends(get_current_user)):
    try:
        return await FHIRClient().get_resource(resource_type, resource_id)
    except Exception as exc:
        raise HTTPException(502, "FHIR repository unavailable") from exc


@router.get("/{resource_type}")
async def search(resource_type: str, _: dict = Depends(get_current_user)):
    return await FHIRClient().search(resource_type, {})


@router.post("/{resource_type}")
async def create(
    resource_type: str,
    resource: FHIRResource,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    payload = resource.model_dump(exclude_none=True)
    if payload.get("resourceType") != resource_type:
        raise HTTPException(422, "FHIR resourceType must match the requested resource type")
    if resource.id:
        raise HTTPException(422, "New FHIR resources must not include an id")
    try:
        _validate_supported_resource(resource)
        health_id = _health_id(resource)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    provider = await session.scalar(
        select(Provider).where(
            Provider.keycloak_subject == user.get("sub"),
            Provider.trust_status == "ACTIVE",
        )
    )
    if provider is None:
        raise HTTPException(403, "No active trusted provider is linked to this principal")

    consent = ConsentService(session)
    consent_allowed = await consent.check_consent(
        health_id, provider.external_id, "TREATMENT", resource_type.lower()
    ) or await consent.check_consent(health_id, provider.external_id, "TREATMENT", "full")
    if not consent_allowed:
        raise HTTPException(403, "No active treatment consent covers this FHIR resource")

    try:
        repository = await _active_repository(session, health_id)
        created = await FHIRClient(repository.base_url).create_resource(resource_type, payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "FHIR repository unavailable") from exc

    await AuditService(session).log_event(
        AuditEventCreate(
            event_type=AuditEventType.RECORD_CREATE,
            health_id=health_id,
            actor_id=user.get("sub", "unknown"),
            action="FHIR resource created",
            payload={
                "resource_type": resource_type,
                "repository_id": str(repository.id),
                "resource_id": created.get("id"),
            },
        )
    )
    await session.commit()
    return created