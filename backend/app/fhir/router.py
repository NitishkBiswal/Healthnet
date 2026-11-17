import json
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.core.database import get_db
from app.fhir.client import FHIRClient
from app.fhir.schemas import FHIRResource
from app.identity.service import IdentityService
from app.provider_trust.models import Provider
from app.provenance.schemas import ProvenanceRecord
from app.provenance.service import ProvenanceService
from app.record_locator.models import RecordLocator
from app.repository.models import Repository
from app.security.dependencies import get_current_user
from app.security.rbac import Role

router = APIRouter(tags=["FHIR"])

ABDM_PROFILE_BASE = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/"
ABDM_RESOURCE_PROFILES = {
    "Patient": "Patient",
    "Encounter": "Encounter",
    "Condition": "Condition",
    "Observation": "Observation",
    "MedicationRequest": "MedicationRequest",
    "DocumentReference": "DocumentReference",
    "Procedure": "Procedure",
    "Immunization": "Immunization",
    "AllergyIntolerance": "AllergyIntolerance",
    "CarePlan": "CarePlan",
    "ServiceRequest": "ServiceRequest",
    "MedicationStatement": "MedicationStatement",
}


def clinical_payload_matches(existing: dict, incoming: dict) -> bool:
    """Treat an identical retry as idempotent, but never overwrite a clinical record."""
    existing_content = dict(existing)
    incoming_content = dict(incoming)
    # Server-managed FHIR metadata changes on read-back; clinical content does not.
    existing_content.pop("meta", None)
    incoming_content.pop("meta", None)
    return json.dumps(existing_content, sort_keys=True, separators=(",", ":")) == json.dumps(
        incoming_content, sort_keys=True, separators=(",", ":")
    )

def apply_abdm_profile(payload: dict) -> dict:
    """Attach the applicable ABDM R4 profile declaration for supported resource types."""
    resource_type = payload.get("resourceType")
    profile_name = ABDM_RESOURCE_PROFILES.get(resource_type)
    if profile_name:
        meta = payload.setdefault("meta", {})
        profiles = meta.setdefault("profile", [])
        canonical = ABDM_PROFILE_BASE + profile_name
        if canonical not in profiles:
            profiles.append(canonical)
    return payload


def _is_admin_or_system(user: dict) -> bool:
    roles = set(user.get("roles", []))
    return Role.ADMIN.value in roles or Role.SYSTEM.value in roles


async def _require_trusted_writer(user: dict, session: AsyncSession) -> None:
    roles = set(user.get("roles", []))
    if _is_admin_or_system(user):
        return
    if Role.PROVIDER.value not in roles:
        raise HTTPException(status_code=403, detail="Provider, admin, or system role required")
    provider = await session.scalar(
        select(Provider).where(
            Provider.keycloak_subject == str(user.get("sub", "")),
            Provider.trust_status == "ACTIVE",
        )
    )
    if provider is None:
        raise HTTPException(status_code=403, detail="An active trusted HealthNet provider record is required")


@router.get("/metadata")
async def metadata(_: dict = Depends(get_current_user)):
    try:
        return await FHIRClient().get_metadata()
    except Exception as exc:
        raise HTTPException(502, "FHIR repository unavailable") from exc


@router.post(
    "/patients/{health_id}/records",
    status_code=status.HTTP_201_CREATED,
    summary="Submit a clinical record to the patient's current repository",
)
async def submit_patient_record(
    health_id: str,
    resource: FHIRResource,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Hospital/provider ingestion endpoint; never accepts a repository URL from the caller."""
    await _require_trusted_writer(user, session)

    patient = await IdentityService(session).get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Health ID not found")

    locator = await session.scalar(
        select(RecordLocator)
        .where(RecordLocator.health_id == health_id, RecordLocator.status == "ACTIVE")
        .with_for_update()
    )
    if locator is None:
        raise HTTPException(status_code=409, detail="Patient has no active repository assignment")

    repository = await session.get(Repository, locator.repository_id)
    if repository is None:
        raise HTTPException(status_code=409, detail="Assigned repository is not registered")
    if repository.status == "OFFLINE":
        raise HTTPException(status_code=503, detail="Patient's current repository is offline")

    payload = resource.model_dump(exclude_none=True)
    resource_type = payload.get("resourceType")
    if not isinstance(resource_type, str) or not resource_type:
        raise HTTPException(status_code=422, detail="FHIR resourceType is required")

    if resource_type == "Patient":
        identifiers = payload.get("identifier", [])
        has_health_id = any(
            item.get("system") == "urn:healthnet:health-id" and item.get("value") == health_id
            for item in identifiers
            if isinstance(item, dict)
        )
        if not has_health_id:
            raise HTTPException(
                status_code=422,
                detail="Patient resource must contain the matching HealthNet Health ID identifier",
            )
        if payload.get("id") not in (None, health_id):
            raise HTTPException(
                status_code=422,
                detail="Patient resource id must match the canonical Health ID in this prototype",
            )
    else:
        reference = payload.get("subject") or payload.get("patient")
        reference_value = reference.get("reference") if isinstance(reference, dict) else None
        if reference_value != f"Patient/{health_id}":
            raise HTTPException(
                status_code=422,
                detail=f"Clinical resource must reference Patient/{health_id}",
            )

    payload = apply_abdm_profile(payload)
    if resource_type == "Patient":
        for identifier in payload.get("identifier", []):
            if isinstance(identifier, dict) and identifier.get("system") == "urn:healthnet:health-id" and identifier.get("value") == health_id:
                identifier.setdefault("type", {"text": "HealthNet Health ID"})
        for name in payload.get("name", []):
            if isinstance(name, dict):
                given = name.get("given", [])
                given_names = given if isinstance(given, list) else [str(given)]
                name.setdefault("text", " ".join([*given_names, name.get("family", "")]).strip())

    resource_id = payload.get("id") or (health_id if resource_type == "Patient" else str(uuid4()))
    payload["id"] = resource_id
    client = FHIRClient(locator.endpoint or repository.base_url)

    # Create a minimal canonical Patient resource on first clinical submission,
    # so incoming resources never point at an absent Patient/{health_id}.
    known_types = [value.strip() for value in locator.resource_types.split(",") if value.strip()]
    if resource_type != "Patient":
        try:
            await client.get_resource("Patient", health_id)
        except Exception:
            patient_resource = {
                "resourceType": "Patient",
                "id": health_id,
                "meta": {"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient"]},
                "identifier": [{"system": "urn:healthnet:health-id", "value": health_id, "type": {"text": "HealthNet Health ID"}}],
                "name": [{"text": f"{patient.given_name} {patient.family_name}", "family": patient.family_name, "given": [patient.given_name]}],
                "birthDate": str(patient.date_of_birth),
            }
            try:
                await client.put_resource("Patient", health_id, patient_resource)
            except Exception as exc:
                await session.rollback()
                raise HTTPException(
                    status_code=502,
                    detail="Could not establish the patient's canonical FHIR Patient resource",
                ) from exc
        if "Patient" not in known_types:
            known_types.append("Patient")

    try:
        if resource_type != "Patient":
            try:
                existing = await client.get_resource(resource_type, resource_id)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
                existing = None

            if existing is not None:
                if not clinical_payload_matches(existing, payload):
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Clinical records are immutable. Submit a corrected record with a new "
                            "resource ID and preserve the original record."
                        ),
                    )
                saved = existing
            else:
                saved = await client.put_resource(resource_type, resource_id, payload)
        else:
            saved = await client.put_resource(resource_type, resource_id, payload)
    except HTTPException:
        await session.rollback()
        raise
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=502, detail="Assigned FHIR repository rejected the record") from exc

    if resource_type not in known_types:
        known_types.append(resource_type)
        locator.resource_types = ",".join(sorted(set(known_types)))

    actor_id = str(user.get("sub", "unknown"))
    source_system = "HEALTHNET_ADMIN" if _is_admin_or_system(user) else "HEALTHNET_TRUSTED_PROVIDER"
    await ProvenanceService(session).record_provenance(
        ProvenanceRecord(
            health_id=health_id,
            repository_id=repository.id,
            resource_type=resource_type,
            resource_id=str(saved.get("id", resource_id)),
            source_system=source_system,
            actor_id=actor_id,
            action="HOSPITAL_INGEST",
            details={"repository_code": repository.code, "submission_mode": "FHIR_API"},
        )
    )
    await AuditService(session).log_event(
        AuditEventCreate(
            event_type=AuditEventType.ACCESS,
            health_id=health_id,
            actor_id=actor_id,
            action="FHIR_RECORD_SUBMITTED",
            payload={
                "repository_code": repository.code,
                "resource_type": resource_type,
                "resource_id": str(saved.get("id", resource_id)),
            },
        )
    )
    await session.commit()
    return {
        "accepted": True,
        "health_id": health_id,
        "repository_code": repository.code,
        "resource_type": resource_type,
        "resource_id": saved.get("id", resource_id),
        "message": "Record stored in the patient's current authoritative repository",
    }


@router.get("/{resource_type}/{resource_id}")
async def get_resource(
    resource_type: str,
    resource_id: str,
    user: dict = Depends(get_current_user),
):
    if not _is_admin_or_system(user):
        raise HTTPException(
            status_code=403,
            detail="Use the consent-checked longitudinal view for patient clinical records",
        )
    try:
        return await FHIRClient().get_resource(resource_type, resource_id)
    except Exception as exc:
        raise HTTPException(502, "FHIR repository unavailable") from exc


@router.get("/{resource_type}")
async def search(
    resource_type: str,
    user: dict = Depends(get_current_user),
):
    if not _is_admin_or_system(user):
        raise HTTPException(
            status_code=403,
            detail="Use the consent-checked longitudinal view for patient clinical records",
        )
    try:
        return await FHIRClient().search(resource_type, {})
    except Exception as exc:
        raise HTTPException(502, "FHIR repository unavailable") from exc


@router.post("/{resource_type}")
async def create(
    resource_type: str,
    resource: FHIRResource,
    user: dict = Depends(get_current_user),
):
    if not _is_admin_or_system(user):
        raise HTTPException(
            status_code=403,
            detail="Use /patients/{health_id}/records so the current repository is resolved",
        )
    try:
        payload = resource.model_dump(exclude_none=True)
        if payload.get("resourceType") != resource_type:
            raise HTTPException(status_code=422, detail="Path resource type does not match resourceType")
        return await FHIRClient().create_resource(resource_type, payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "FHIR repository unavailable") from exc
