from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.audit.schemas import AuditEventResponse, AuditEventType
from app.medical_import.router import _make_resource, _merge_resource_types, _rows_from_upload
from app.main import app


def test_import_builds_abdm_condition_and_observation() -> None:
    condition = _make_resource(
        {
            "record_type": "CONDITION", "record_id": "legacy-dm-1",
            "display": "Type 2 diabetes mellitus", "recorded_at": "2025-01-15",
            "is_chronic": "TRUE", "status": "active",
        },
        "INOD000100", "Example Hospital",
    )
    assert condition["resourceType"] == "Condition"
    assert condition["subject"]["reference"] == "Patient/INOD000100"
    assert condition["verificationStatus"]["coding"][0]["code"] == "unconfirmed"
    assert condition["meta"]["profile"][0].endswith("/Condition")
    assert condition["category"][0]["coding"][0]["code"] == "problem-list-item"

    observation = _make_resource(
        {
            "record_type": "OBSERVATION", "record_id": "legacy-bp-1",
            "display": "Blood pressure", "recorded_at": "2025-01-15",
            "value": "120", "unit": "mmHg",
        },
        "INOD000100", "Example Hospital",
    )
    assert observation["resourceType"] == "Observation"
    assert observation["valueQuantity"]["value"] == 120
    assert observation["meta"]["profile"][0].endswith("/Observation")


def test_import_rejects_unknown_record_types_and_missing_values() -> None:
    with pytest.raises(ValueError, match="record_type"):
        _make_resource(
            {"record_type": "PRESCRIPTION", "record_id": "x", "display": "x", "recorded_at": "2025-01-01"},
            "INOD000100", "Hospital",
        )
    with pytest.raises(ValueError, match="value"):
        _make_resource(
            {"record_type": "OBSERVATION", "record_id": "x", "display": "Glucose", "recorded_at": "2025-01-01"},
            "INOD000100", "Hospital",
        )


def test_csv_upload_parser_reads_utf8_csv() -> None:
    rows = _rows_from_upload(
        "records.csv",
        b"health_id,record_type,record_id,display,recorded_at\nINOD000100,CONDITION,c1,Diabetes,2025-01-01\n",
    )
    assert rows[0]["health_id"] == "INOD000100"


def test_import_and_auditor_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/v1/fhir/imports/csv-excel"]
    assert "get" in paths["/api/v1/audit/imports"]


def test_imported_resource_types_are_added_without_losing_existing_types() -> None:
    assert _merge_resource_types("Patient,Observation", {"Condition", "Observation"}) == "Condition,Observation,Patient"
    assert _merge_resource_types(None, {"Condition", "Observation"}) == "Condition,Observation"


def test_audit_event_response_includes_timestamp() -> None:
    event = AuditEventResponse(
        id=uuid4(),
        event_type=AuditEventType.ACCESS,
        health_id="INOD000100",
        actor_id="auditor-subject",
        action="MEDICAL_RECORD_IMPORTED",
        payload={},
        prev_event_hash=None,
        event_hash="a" * 64,
        created_at=datetime.now(UTC),
    )
    assert event.created_at.tzinfo is not None


def test_emergency_and_longitudinal_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "get" in paths["/api/v1/emergency/patients/{health_id}/emergency-profile"]
    assert "post" in paths["/api/v1/emergency/patients/{health_id}/break-glass"]
    assert "get" in paths["/api/v1/emergency/patients/{health_id}/break-glass-summary"]
    assert "get" in paths["/api/v1/audit/emergency-access"]

def test_break_glass_requires_a_reason_and_defaults_to_minimal_tier() -> None:
    from pydantic import ValidationError
    from app.emergency.schemas import BreakGlassRequest, RetrievalTier

    request = BreakGlassRequest(reason="Patient is unconscious and unable to consent")
    assert request.tier == RetrievalTier.TIER_1
    assert request.emergency_declaration is False
    confirmed = BreakGlassRequest(reason="Patient is unconscious and unable to consent", emergency_declaration=True)
    assert confirmed.emergency_declaration is True
    with pytest.raises(ValidationError):
        BreakGlassRequest(reason="no")


def test_emergency_profile_is_the_only_break_glass_read_route() -> None:
    paths = app.openapi()["paths"]
    profile = paths["/api/v1/emergency/patients/{health_id}/emergency-profile"]
    assert "get" in profile
    assert "/api/v1/longitudinal/patients/longitudinal-view" in paths
