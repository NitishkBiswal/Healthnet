from pydantic import ValidationError
import pytest

from app.fhir.schemas import FHIRResource
from app.main import app
from app.migration.schemas import TransferExecuteRequest


def test_fhir_resource_preserves_clinical_payload_fields() -> None:
    resource = FHIRResource.model_validate(
        {
            "resourceType": "Observation",
            "status": "final",
            "subject": {"reference": "Patient/INOD000100"},
            "valueQuantity": {"value": 128, "unit": "mmHg"},
        }
    )
    payload = resource.model_dump(exclude_none=True)
    assert payload["resourceType"] == "Observation"
    assert payload["subject"]["reference"] == "Patient/INOD000100"
    assert payload["valueQuantity"]["value"] == 128


def test_transfer_execution_requires_one_time_authorization_token() -> None:
    with pytest.raises(ValidationError):
        TransferExecuteRequest(resource_count=0)


def test_transfer_execution_accepts_token_and_server_discovered_count() -> None:
    request = TransferExecuteRequest(
        authorization_token="a-valid-demo-token-value-over-20",
        resource_count=0,
    )
    assert request.resource_count == 0
    assert request.package_hash is None


def test_hospital_ingestion_route_is_registered() -> None:
    route = app.openapi()["paths"]["/api/v1/fhir/patients/{health_id}/records"]
    assert "post" in route


def test_patient_consent_revocation_route_is_registered() -> None:
    route = app.openapi()["paths"]["/api/v1/consent/consents/{consent_id}"]
    assert "delete" in route


def test_abdm_r4_profile_is_added_to_supported_resources() -> None:
    from app.fhir.router import apply_abdm_profile

    resource = apply_abdm_profile({"resourceType": "Observation", "status": "final"})
    assert resource["meta"]["profile"] == [
        "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Observation"
    ]



def test_clinical_records_allow_identical_retries_but_reject_edits() -> None:
    from app.fhir.router import clinical_payload_matches

    original = {
        "resourceType": "Observation",
        "id": "obs-1",
        "status": "final",
        "valueQuantity": {"value": 120, "unit": "mmHg"},
        "meta": {"versionId": "1"},
    }
    retry = {
        "resourceType": "Observation",
        "id": "obs-1",
        "status": "final",
        "valueQuantity": {"value": 120, "unit": "mmHg"},
        "meta": {"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Observation"]},
    }
    corrected = {**retry, "valueQuantity": {"value": 130, "unit": "mmHg"}}
    assert clinical_payload_matches(original, retry)
    assert not clinical_payload_matches(original, corrected)


def test_patient_aadhaar_self_service_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "get" in paths["/api/v1/identity/me/aadhaar"]
    assert "put" in paths["/api/v1/identity/me/aadhaar"]
