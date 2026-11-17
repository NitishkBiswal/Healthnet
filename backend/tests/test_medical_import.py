from datetime import date

import pytest

from app.medical_import.router import _make_resource, _rows_from_upload
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
