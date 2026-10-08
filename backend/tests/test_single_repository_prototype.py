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
