from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.consent.service import ConsentService
from app.core.database import get_db
from app.core.rate_limit import fhir_write_limit
from app.emergency.service import EmergencyService
from app.fhir.client import FHIRClient, FHIRClientError
from app.fhir.schemas import FHIRResource
from app.provider_trust.models import Provider
from app.provenance.schemas import ProvenanceRecord
from app.provenance.service import ProvenanceService
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
    "Observation": ("status", "code"),
    "Procedure": ("status", "code"),
}


def _validate_supported_resource(resource: FHIRResource) -> None:
    payload = resource.model_dump(exclude_none=True)
    resource_type = payload.get("resourceType")
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        raise ValueError(f"FHIR resource type {resource_type} is not supported")
    missing = [
        field for field in REQUIRED_RESOURCE_FIELDS[resource_type] if field not in payload
    ]
    if missing:
        raise ValueError(
            f"FHIR resource is missing required field(s): {', '.join(missing)}"
        )


def _health_id(payload: dict[str, Any] | FHIRResource) -> str:
    if isinstance(payload, FHIRResource):
        payload = payload.model_dump(exclude_none=True)
    reference = None
    for field in ("subject", "patient"):
        value = payload.get(field)
        if isinstance(value, dict) and isinstance(value.get("reference"), str):
            reference = value["reference"]
            break
    if not reference or not reference.startswith("Patient/"):
        raise ValueError("FHIR resource must reference Patient/<Health ID>")
    health_id = reference.removeprefix("Patient/").strip()
    if not health_id or "/" in health_id:
        raise ValueError("FHIR patient reference must contain a Health ID")
    return health_id


async def _active_repository(session: AsyncSession, health_id: str) -> Repository:
    custody = await session.scalar(
        select(EHRCustody)
        .where(
            EHRCustody.health_id == health_id,
            EHRCustody.custody_end.is_(None),
        )
        .order_by(EHRCustody.custody_start.desc())
    )
    if custody is None:
        raise ValueError("No active repository is configured for this patient")
    repository = await session.get(Repository, custody.repository_id)
    if repository is None or repository.status == RepositoryStatus.OFFLINE:
        raise ValueError("The active repository is unavailable")
    return repository


async def _trusted_provider(session: AsyncSession, user: dict[str, Any]) -> Provider:
    provider = await session.scalar(
        select(Provider).where(
            Provider.keycloak_subject == user.get("sub"),
            Provider.trust_status == "ACTIVE",
        )
    )
    if provider is None:
        raise HTTPException(403, "No active trusted provider is linked to this principal")
    return provider


async def _authorize_record_access(
    session: AsyncSession,
    provider: Provider,
    health_id: str,
    resource_type: str,
    user: dict[str, Any],
    break_glass_token: str | None,
    *,
    allow_break_glass: bool,
) -> None:
    consent = ConsentService(session)
    allowed = await consent.check_consent(
        health_id, provider.external_id, "TREATMENT", resource_type.lower()
    ) or await consent.check_consent(
        health_id, provider.external_id, "TREATMENT", "full"
    )
    if allowed:
        return
    if allow_break_glass and await EmergencyService(session).validate_break_glass(
        health_id, str(user.get("sub", "")), break_glass_token
    ):
        return
    raise HTTPException(403, "No active treatment consent covers this FHIR resource")


def _fhir_error(exc: FHIRClientError) -> HTTPException:
    detail: dict[str, Any] = {"message": str(exc)}
    if exc.operation_outcome:
        detail["operation_outcome"] = exc.operation_outcome
    return HTTPException(502, detail)


async def _record_audit(
    session: AsyncSession,
    event_type: AuditEventType,
    health_id: str,
    user: dict[str, Any],
    action: str,
    resource_type: str,
    resource_id: str | None,
) -> None:
    await AuditService(session).log_event(
        AuditEventCreate(
            event_type=event_type,
            health_id=health_id,
            actor_id=str(user.get("sub", "unknown")),
            action=action,
            payload={"resource_type": resource_type, "resource_id": resource_id},
        )
    )


async def _record_provenance(
    session: AsyncSession,
    health_id: str,
    repository: Repository,
    user: dict[str, Any],
    action: str,
    resource_type: str,
    resource_id: str | None,
) -> None:
    if not resource_id:
        return
    await ProvenanceService(session).record_provenance(
        ProvenanceRecord(
            health_id=health_id,
            repository_id=repository.id,
            resource_type=resource_type,
            resource_id=resource_id,
            source_system=repository.code,
            actor_id=str(user.get("sub", "unknown")),
            action=action,
            details={"source": "HealthNet FHIR API"},
        )
    )


@router.get("/metadata")
async def metadata(_: dict = Depends(get_current_user)):
    try:
        return await FHIRClient().get_metadata()
    except FHIRClientError as exc:
        raise _fhir_error(exc) from exc


@router.get("/{resource_type}/{resource_id}")
async def get_resource(
    resource_type: str,
    resource_id: str,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
    break_glass_token: str | None = Header(default=None, alias="X-Break-Glass-Token"),
):
    provider = await _trusted_provider(session, user)
    try:
        resource = await FHIRClient().get_resource(resource_type, resource_id)
        health_id = _health_id(resource)
        await _authorize_record_access(
            session,
            provider,
            health_id,
            resource_type,
            user,
            break_glass_token,
            allow_break_glass=True,
        )
        await _record_audit(
            session, AuditEventType.RETRIEVAL, health_id, user,
            "FHIR resource retrieved", resource_type, resource_id,
        )
        await session.commit()
        return resource
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FHIRClientError as exc:
        raise _fhir_error(exc) from exc


@router.get("/{resource_type}")
async def search(
    resource_type: str,
    request: Request,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
    break_glass_token: str | None = Header(default=None, alias="X-Break-Glass-Token"),
):
    provider = await _trusted_provider(session, user)
    params = dict(request.query_params)
    reference = params.get("subject") or params.get("patient")
    if not reference:
        raise HTTPException(422, "FHIR search requires a patient or subject parameter")
    try:
        health_id = (
            reference.removeprefix("Patient/").strip()
            if reference.startswith("Patient/")
            else reference.strip()
        )
        if not health_id or "/" in health_id:
            raise ValueError("FHIR patient reference must contain a Health ID")
        await _authorize_record_access(
            session,
            provider,
            health_id,
            resource_type,
            user,
            break_glass_token,
            allow_break_glass=True,
        )
        repository = await _active_repository(session, health_id)
        bundle = await FHIRClient(repository.base_url).search(resource_type, params)
        await _record_audit(
            session, AuditEventType.RETRIEVAL, health_id, user,
            "FHIR resources searched", resource_type, None,
        )
        await session.commit()
        return bundle
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except FHIRClientError as exc:
        raise _fhir_error(exc) from exc


@router.post("/{resource_type}", dependencies=[Depends(fhir_write_limit)])
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
        health_id = _health_id(payload)
        provider = await _trusted_provider(session, user)
        await _authorize_record_access(
            session, provider, health_id, resource_type, user, None,
            allow_break_glass=False,
        )
        repository = await _active_repository(session, health_id)
        created = await FHIRClient(repository.base_url).create_resource(
            resource_type, payload
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except FHIRClientError as exc:
        raise _fhir_error(exc) from exc

    await _record_audit(
        session,
        AuditEventType.RECORD_CREATE,
        health_id,
        user,
        "FHIR resource created",
        resource_type,
        created.get("id"),
    )
    await _record_provenance(
        session, health_id, repository, user, "CREATE",
        resource_type, created.get("id"),
    )
    await session.commit()
    return created


async def _load_authorized_resource(
    resource_type: str,
    resource_id: str,
    session: AsyncSession,
    user: dict[str, Any],
) -> tuple[Provider, dict[str, Any], str, Repository]:
    provider = await _trusted_provider(session, user)
    resource = await FHIRClient().get_resource(resource_type, resource_id)
    health_id = _health_id(resource)
    await _authorize_record_access(
        session,
        provider,
        health_id,
        resource_type,
        user,
        None,
        allow_break_glass=False,
    )
    repository = await _active_repository(session, health_id)
    return provider, resource, health_id, repository


@router.put(
    "/{resource_type}/{resource_id}",
    dependencies=[Depends(fhir_write_limit)],
)
async def update(
    resource_type: str,
    resource_id: str,
    resource: FHIRResource,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    payload = resource.model_dump(exclude_none=True)
    if payload.get("resourceType") != resource_type:
        raise HTTPException(422, "FHIR resourceType must match the requested resource type")
    try:
        _validate_supported_resource(resource)
        if resource.id not in {None, resource_id}:
            raise ValueError("FHIR resource id must match the requested resource id")
        _, current, health_id, repository = await _load_authorized_resource(
            resource_type, resource_id, session, user
        )
        if _health_id(payload) != health_id:
            raise ValueError("FHIR resource patient reference cannot be changed")
        updated = await FHIRClient(repository.base_url).update_resource(
            resource_type, resource_id, payload
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FHIRClientError as exc:
        raise _fhir_error(exc) from exc
    await _record_audit(
        session, AuditEventType.RECORD_UPDATE, health_id, user,
        "FHIR resource updated", resource_type, updated.get("id") or current.get("id"),
    )
    await _record_provenance(
        session, health_id, repository, user, "UPDATE",
        resource_type, updated.get("id") or current.get("id"),
    )
    await session.commit()
    return updated


@router.patch(
    "/{resource_type}/{resource_id}",
    dependencies=[Depends(fhir_write_limit)],
)
async def patch(
    resource_type: str,
    resource_id: str,
    operations: list[dict[str, Any]],
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    forbidden_paths = {"/id", "/resourceType", "/subject", "/patient"}
    for operation in operations:
        path = operation.get("path")
        if not isinstance(path, str) or any(
            path == forbidden or path.startswith(forbidden + "/")
            for forbidden in forbidden_paths
        ):
            raise HTTPException(422, "FHIR PATCH cannot change resource identity or patient")
    try:
        _, current, health_id, repository = await _load_authorized_resource(
            resource_type, resource_id, session, user
        )
        updated = await FHIRClient(repository.base_url).patch_resource(
            resource_type, resource_id, operations
        )
        if updated and _health_id(updated) != health_id:
            raise ValueError("FHIR PATCH cannot change the patient reference")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FHIRClientError as exc:
        raise _fhir_error(exc) from exc
    await _record_audit(
        session, AuditEventType.RECORD_UPDATE, health_id, user,
        "FHIR resource partially updated", resource_type, updated.get("id") or resource_id,
    )
    await _record_provenance(
        session, health_id, repository, user, "UPDATE",
        resource_type, updated.get("id") or current.get("id") or resource_id,
    )
    await session.commit()
    return updated


@router.delete(
    "/{resource_type}/{resource_id}",
    dependencies=[Depends(fhir_write_limit)],
)
async def delete(
    resource_type: str,
    resource_id: str,
    user: dict = Depends(require_provider),
    session: AsyncSession = Depends(get_db),
):
    try:
        _, current, health_id, repository = await _load_authorized_resource(
            resource_type, resource_id, session, user
        )
        updated = await FHIRClient(repository.base_url).delete_resource(
            resource_type, resource_id
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except FHIRClientError as exc:
        raise _fhir_error(exc) from exc
    await _record_audit(
        session, AuditEventType.RECORD_DELETE, health_id, user,
        "FHIR resource marked inactive", resource_type, updated.get("id") or resource_id,
    )
    await _record_provenance(
        session, health_id, repository, user, "DELETE",
        resource_type, updated.get("id") or current.get("id") or resource_id,
    )
    await session.commit()
    return updated
