from app.identity.identifiers import decrypt_aadhaar, encrypt_aadhaar
from app.identity.schemas import AadhaarUpdateRequest, PatientRegistrationRequest, PatientResponse
from pydantic import ValidationError
import pytest


def test_aadhaar_is_optional_and_requires_twelve_digit_format() -> None:
    request = PatientRegistrationRequest(
        given_name="Test",
        family_name="Patient",
        date_of_birth="2000-01-01",
        issuing_jurisdiction="IN-WB",
    )
    assert request.aadhaar_number is None

    with pytest.raises(ValidationError):
        PatientRegistrationRequest(
            given_name="Test",
            family_name="Patient",
            date_of_birth="2000-01-01",
            issuing_jurisdiction="IN-WB",
            aadhaar_number="1234",
        )


def test_aadhaar_encryption_round_trip_and_ciphertext_is_not_plaintext() -> None:
    aadhaar = "123456789012"
    encrypted = encrypt_aadhaar(aadhaar)
    assert encrypted != aadhaar
    assert aadhaar not in encrypted
    assert decrypt_aadhaar(encrypted) == aadhaar


def test_patient_api_response_never_contains_aadhaar_fields() -> None:
    assert "aadhaar_encrypted" not in PatientResponse.model_fields
    assert "aadhaar_last4" not in PatientResponse.model_fields


def test_patient_can_update_aadhaar_with_format_only_validation() -> None:
    request = AadhaarUpdateRequest(aadhaar_number="123456789012")
    assert request.aadhaar_number.get_secret_value() == "123456789012"

    with pytest.raises(ValidationError):
        AadhaarUpdateRequest(aadhaar_number="not-an-aadhaar")


def test_aadhaar_cannot_be_saved_through_plaintext_identifier_list() -> None:
    with pytest.raises(ValidationError):
        PatientRegistrationRequest(
            given_name="Test",
            family_name="Patient",
            date_of_birth="2000-01-01",
            issuing_jurisdiction="IN-WB",
            identifiers=[{"identifier_type": "AADHAAR", "identifier_value": "123456789012"}],
        )
