from datetime import date
from uuid import uuid4

from app.identity.models import PatientIdentity
from app.identity.schemas import PatientRegistrationRequest
from app.identity.service import IdentityService


def make_request(**overrides: object) -> PatientRegistrationRequest:
    data: dict[str, object] = {
        "given_name": "Ananya",
        "family_name": "Sharma",
        "date_of_birth": date(1995, 5, 12),
        "sex": "F",
        "phone": "+919876543210",
        "email": "ananya@example.test",
        "issuing_jurisdiction": "IN-OD",
    }
    data.update(overrides)
    return PatientRegistrationRequest.model_validate(data)


def test_health_id_prefix_matches_srs_example() -> None:
    assert IdentityService.health_id_prefix("IN-OD") == "INOD"
    assert IdentityService.health_id_prefix("in_od") == "INOD"


def test_similarity_is_high_for_same_demographics() -> None:
    request = make_request()
    patient = PatientIdentity(
        id=uuid4(),
        display_health_id="INOD000001",
        issuing_jurisdiction="IN-OD",
        given_name="Ananya",
        family_name="Sharma",
        date_of_birth=date(1995, 5, 12),
        sex="F",
        phone="+919876543210",
        email="ananya@example.test",
    )
    score = IdentityService._similarity(request, patient)
    assert score == 1.0


def test_similarity_is_lower_for_different_patient() -> None:
    request = make_request()
    patient = PatientIdentity(
        id=uuid4(),
        display_health_id="INOD000002",
        issuing_jurisdiction="IN-OD",
        given_name="Rahul",
        family_name="Patel",
        date_of_birth=date(1980, 1, 1),
        sex="M",
        phone="+911111111111",
        email="rahul@example.test",
    )
    score = IdentityService._similarity(request, patient)
    assert score < IdentityService.MEDIUM_CONFIDENCE
