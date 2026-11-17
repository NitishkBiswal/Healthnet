"""Admin-only CSV/XLSX import into each patient's authoritative FHIR repository.

Expected columns: health_id, record_type (CONDITION|OBSERVATION), record_id,
display, code, status, recorded_at, value, unit, source_hospital,
is_chronic, emergency_relevant.
"""
import csv
import hashlib
import io
from datetime import date, datetime
from typing import Any
from zipfile import BadZipFile

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.core.database import get_db
from app.emergency.models import EmergencyHealthProfile
from app.fhir.client import FHIRClient
from app.fhir.router import apply_abdm_profile, clinical_payload_matches
from app.identity.service import IdentityService
from app.provenance.schemas import ProvenanceRecord
from app.provenance.service import ProvenanceService
from app.record_locator.models import RecordLocator
from app.repository.models import Repository
from app.security.dependencies import require_role
from app.security.rbac import Role

router = APIRouter(tags=["Medical Record Import"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 5000
REQUIRED_COLUMNS = {"health_id", "record_type", "record_id", "display", "recorded_at"}


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _rows_from_upload(filename: str, content: bytes) -> list[dict[str, Any]]:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "csv":
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV must contain a header row")
        rows = []
        for row in reader:
            rows.append(dict(row))
            if len(rows) > MAX_ROWS:
                raise ValueError(f"Upload exceeds the {MAX_ROWS}-row limit")
    elif suffix in {"xlsx", "xlsm"}:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        values = sheet.iter_rows(values_only=True)
        headers = [str(value).strip() if value is not None else "" for value in next(values, ())]
        rows = []
        for row in values:
            if any(value is not None for value in row):
                rows.append(dict(zip(headers, row)))
                if len(rows) > MAX_ROWS:
                    workbook.close()
                    raise ValueError(f"Upload exceeds the {MAX_ROWS}-row limit")
        workbook.close()
    else:
        raise ValueError("Only .csv, .xlsx and .xlsm files are supported")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"Upload exceeds the {MAX_ROWS}-row limit")
    return rows


def _date(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value or "").strip()


def _make_resource(row: dict[str, Any], health_id: str, source_hospital: str) -> dict[str, Any]:
    kind = str(row.get("record_type", "")).strip().upper()
    resource_id = str(row.get("record_id", "")).strip()
    display = str(row.get("display", "")).strip()
    code = str(row.get("code", "") or "").strip()
    recorded_at = _date(row.get("recorded_at"))
    if not resource_id or not display or not recorded_at:
        raise ValueError("record_id, display and recorded_at are required")
    try:
        datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError:
        try:
            date.fromisoformat(recorded_at)
        except ValueError as exc:
            raise ValueError("recorded_at must be an ISO date or datetime") from exc
    coding: dict[str, Any] = {"text": display}
    if code:
        default_system = "http://loinc.org" if kind == "OBSERVATION" else "http://snomed.info/sct"
        coding["coding"] = [{"system": str(row.get("code_system") or default_system), "code": code, "display": display}]
    if kind == "CONDITION":
        status = str(row.get("status") or "unknown").strip().lower()
        allowed = {"active", "recurrence", "relapse", "inactive", "remission", "resolved", "unknown"}
        if status not in allowed:
            raise ValueError("Condition status must be active, inactive, resolved, remission, or unknown")
        resource = {
            "resourceType": "Condition",
            "id": resource_id,
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": status}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "unconfirmed"}]},
            "code": coding,
            "subject": {"reference": f"Patient/{health_id}"},
            "recordedDate": recorded_at,
            "note": [{"text": f"Imported from {source_hospital}; source verification status not independently established."}],
        }
        if _truthy(row.get("is_chronic")):
            resource["category"] = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]}]
        return apply_abdm_profile(resource)
    if kind == "OBSERVATION":
        value = row.get("value")
        if value is None or str(value).strip() == "":
            raise ValueError("Observation rows require a value")
        try:
            numeric = float(value)
            value_x: dict[str, Any] = {"valueQuantity": {"value": numeric, "unit": str(row.get("unit") or ""), "system": "http://unitsofmeasure.org"}}
        except (ValueError, TypeError):
            value_x = {"valueString": str(value)}
        resource = {
            "resourceType": "Observation",
            "id": resource_id,
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey"}]}],
            "code": coding,
            "subject": {"reference": f"Patient/{health_id}"},
            "effectiveDateTime": recorded_at,
            **value_x,
            "note": [{"text": f"Imported from {source_hospital}; source verification status not independently established."}],
        }
        return apply_abdm_profile(resource)
    raise ValueError("record_type must be CONDITION or OBSERVATION")


async def _add_emergency_condition(session: AsyncSession, health_id: str, display: str) -> None:
    profile = await session.scalar(select(EmergencyHealthProfile).where(EmergencyHealthProfile.health_id == health_id))
    if profile is None:
        profile = EmergencyHealthProfile(health_id=health_id)
        session.add(profile)
        await session.flush()
    existing = [item.strip() for item in (profile.conditions or "").split(",") if item.strip()]
    if display.casefold() not in {item.casefold() for item in existing}:
        existing.append(display)
        profile.conditions = ", ".join(existing)


@router.post("/imports/csv-excel")
async def import_csv_excel(
    file: UploadFile = File(...),
    user: dict = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Upload must be 10 MB or smaller")
    digest = hashlib.sha256(content).hexdigest()
    try:
        rows = _rows_from_upload(file.filename or "", content)
    except (ValueError, UnicodeDecodeError, BadZipFile, InvalidFileException) as exc:
        raise HTTPException(422, str(exc)) from exc
    if not rows:
        raise HTTPException(422, "The uploaded file contains no data rows")
    headers = {str(key).strip().lower() for key in rows[0]}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise HTTPException(422, f"Missing required columns: {', '.join(sorted(missing))}")

    actor_id = str(user.get("sub", "unknown"))
    imported = 0
    failed: list[dict[str, Any]] = []
    emergency_added = 0
    touched_health_ids: set[str] = set()

    for index, raw in enumerate(rows, start=2):
        row = {str(key).strip().lower(): value for key, value in raw.items() if key is not None}
        health_id = str(row.get("health_id") or "").strip()
        source_hospital = str(row.get("source_hospital") or "Unspecified source hospital").strip()
        savepoint = await session.begin_nested()
        resource_written = False
        written_client = None
        written_type = None
        written_id = None
        try:
            if not health_id:
                raise ValueError("health_id is required")
            patient = await IdentityService(session).get_patient_by_health_id(health_id)
            if patient is None:
                raise ValueError("HealthNet Health ID was not found")
            locator = await session.scalar(select(RecordLocator).where(RecordLocator.health_id == health_id, RecordLocator.status == "ACTIVE").with_for_update())
            if locator is None:
                raise ValueError("Patient has no active repository assignment")
            repository = await session.get(Repository, locator.repository_id)
            if repository is None or repository.status == "OFFLINE":
                raise ValueError("Patient's assigned repository is unavailable")
            resource = _make_resource(row, health_id, source_hospital)
            resource_type = resource["resourceType"]
            client = FHIRClient(locator.endpoint or repository.base_url)
            try:
                await client.get_resource("Patient", health_id)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
                patient_resource = apply_abdm_profile({
                    "resourceType": "Patient",
                    "id": health_id,
                    "identifier": [{"system": "urn:healthnet:health-id", "value": health_id, "type": {"text": "HealthNet Health ID"}}],
                    "name": [{"text": f"{patient.given_name} {patient.family_name}", "family": patient.family_name, "given": [patient.given_name]}],
                    "birthDate": str(patient.date_of_birth),
                })
                await client.put_resource("Patient", health_id, patient_resource)
            try:
                existing = await client.get_resource(resource_type, resource["id"])
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
                existing = None
            if existing is not None:
                if clinical_payload_matches(existing, resource):
                    raise ValueError("Duplicate row: this exact clinical resource already exists")
                raise ValueError("Resource ID already exists with different clinical content; use a new record_id")
            await client.put_resource(resource_type, resource["id"], resource)
            resource_written = True
            written_client, written_type, written_id = client, resource_type, resource["id"]
            await ProvenanceService(session).record_provenance(ProvenanceRecord(
                health_id=health_id, repository_id=repository.id, resource_type=resource_type,
                resource_id=resource["id"], source_system=source_hospital, actor_id=actor_id,
                action="BULK_FILE_IMPORT", details={"file_sha256": digest, "row_number": index},
            ))
            await AuditService(session).log_event(AuditEventCreate(
                event_type=AuditEventType.ACCESS, health_id=health_id, actor_id=actor_id,
                action="MEDICAL_RECORD_IMPORTED",
                payload={"resource_type": resource_type, "resource_id": resource["id"], "source_hospital": source_hospital, "file_sha256": digest, "row_number": index},
            ))
            if resource_type == "Condition" and _truthy(row.get("is_chronic")) and _truthy(row.get("emergency_relevant")):
                await _add_emergency_condition(session, health_id, str(row.get("display")).strip())
                emergency_added += 1
            supported_types = {value.strip() for value in (locator.resource_types or "").split(",") if value.strip()}
            supported_types.update({"Condition", "Observation"})
            locator.resource_types = ",".join(sorted(supported_types))
            await savepoint.commit()
            # Commit each row's SQL metadata alongside its external FHIR write.
            # If SQL fails, compensate the FHIR write in the exception handler.
            await session.commit()
            imported += 1
            touched_health_ids.add(health_id)
        except Exception as exc:
            await session.rollback()
            cleanup_note = ""
            if resource_written and written_client and written_type and written_id:
                try:
                    await written_client.delete_resource(written_type, written_id)
                except Exception as cleanup_exc:
                    cleanup_note = f"; FHIR compensation failed ({type(cleanup_exc).__name__}); reconcile resource {written_type}/{written_id}"
            failed.append({"row": index, "health_id": health_id or None, "error": (str(exc)[:220] + cleanup_note)[:300]})
    return {
        "accepted": imported,
        "failed": len(failed),
        "emergency_conditions_added": emergency_added,
        "patients_affected": len(touched_health_ids),
        "file_sha256": digest,
        "errors": failed[:100],
        "message": "Imported rows were routed using each patient's active Record Locator. Failed rows were not committed.",
    }
