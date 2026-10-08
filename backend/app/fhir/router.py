from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.fhir.client import FHIRClient
from app.fhir.schemas import FHIRResource
from app.identity.service import IdentityService
from app.provider_trust.models import Provider
from app.record_locator.models import RecordLocator
from app.repository.models import Repository
from app.security.dependencies import get_current_user
from app.security.rbac import Role

router = APIRouter(tags=["FHIR"])


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
    else:
        reference = payload.get("subject") or payload.get("patient")
        reference_value = reference.get("reference") if isinstance(reference, dict) else None
        if reference_value != f"Patient/{health_id}":
            raise HTTPException(
                status_code=422,
                detail=f"Clinical resource must reference Patient/{health_id}",
            )

    resource_id = payload.get("id") or str(uuid4())
    payload["id"] = resource_id
    client = FHIRClient(locator.endpoint or repository.base_url)
    try:
        saved = await client.put_resource(resource_type, resource_id, payload)
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=502, detail="Assigned FHIR repository rejected the record") from exc

    known_types = [value.strip() for value in locator.resource_types.split(",") if value.strip()]
    if resource_type not in known_types:
        known_types.append(resource_type)
        locator.resource_types = ",".join(sorted(set(known_types)))
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
