import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.authorization.service import AuthorizationService
from app.consent.models import Consent
from app.consent.service import ConsentService
from app.fhir.router import _health_id
from app.identity.models import PatientIdentity
from app.migration.models import TransferRequest
from app.migration.schemas import MigrationState
from app.migration.service import MigrationService
from app.fhir.schemas import FHIRResource
from app.repository.models import EHRCustody, Repository
from app.repository.schemas import CustodyChangeRequest
from app.repository.service import RepositoryService


class ScalarResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self.values


class EmptySession:
    def __init__(self):
        self.added = []

    async def get(self, model, identity):
        return None

    async def execute(self, statement):
        return ScalarResult([])

    async def scalar(self, statement):
        return None

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        return None


def test_revoke_consent_is_idempotent_guarded():
    session = EmptySession()
    consent = Consent(
        id=uuid4(),
        health_id="INOD000001",
        grantee_type="PROVIDER",
        grantee_id="PRV-1",
        purpose="TREATMENT",
        scopes="clinical",
        status="ACTIVE",
        valid_from=datetime.now(UTC),
    )
    service = ConsentService(session)
    service.get_consent = AsyncMock(return_value=consent)

    revoked = asyncio.run(service.revoke_consent(consent.id))
    assert revoked.status == "REVOKED"
    assert revoked.revoked_at is not None

    with pytest.raises(ValueError, match="already been revoked"):
        asyncio.run(service.revoke_consent(consent.id))


def test_authorization_rejects_roles_without_permission():
    allowed, reason = asyncio.run(
        AuthorizationService(EmptySession()).authorize_request(
            SimpleNamespace(
                grantee_id="someone",
                health_id="INOD000001",
                purpose="TREATMENT",
                scope="clinical",
            ),
            {"sub": "nobody", "roles": ["AUDITOR"]},
        )
    )
    assert allowed is False
    assert "not authorized" in reason


def test_fhir_subject_must_be_health_id_reference():
    resource = FHIRResource.model_validate(
        {"resourceType": "Observation", "subject": {"reference": "Patient/INOD000001"}}
    )
    assert _health_id(resource) == "INOD000001"

    invalid = FHIRResource.model_validate(
        {"resourceType": "Observation", "subject": {"reference": "Device/123"}}
    )
    with pytest.raises(ValueError, match="Patient/<Health ID>"):
        _health_id(invalid)


def test_repository_change_is_committed_only_after_validation(monkeypatch):
    target = Repository(
        id=uuid4(), code="IN-KA", name="Karnataka",
        jurisdiction="IN-KA", base_url="https://repository.example.test/fhir",
        status="ONLINE",
    )

    class Session(EmptySession):
        async def get(self, model, identity):
            return target

    class ValidatedFHIR:
        def __init__(self, base_url):
            assert base_url == target.base_url

        async def get_metadata(self):
            return {"resourceType": "CapabilityStatement"}

    async def validated_url(base_url):
        assert base_url == target.base_url

    monkeypatch.setattr("app.repository.service.validate_repository_url", validated_url)
    monkeypatch.setattr("app.repository.service.FHIRClient", lambda base_url: ValidatedFHIR(base_url))
    session = Session()
    replacement = asyncio.run(
        RepositoryService(session).change_custody_repository(
            "INOD000001",
            CustodyChangeRequest(repository_id=target.id),
        )
    )

    assert isinstance(replacement, EHRCustody)
    assert replacement.health_id == "INOD000001"
    assert replacement.repository_id == target.id
    assert any(isinstance(item, EHRCustody) for item in session.added)


def test_patient_may_authorize_only_owned_transfer():
    transfer = TransferRequest(
        id=uuid4(),
        health_id="INOD000001",
        source_repository_id=uuid4(),
        destination_repository_id=uuid4(),
        requested_by="admin-1",
        purpose="Migration",
        scope="All records",
        state=MigrationState.REQUESTED.value,
    )
    patient = PatientIdentity(
        display_health_id="INOD000001",
        issuing_jurisdiction="IN",
        given_name="Patient",
        family_name="One",
        date_of_birth=datetime(1990, 1, 1).date(),
        owner_subject="patient-1",
    )

    class Session(EmptySession):
        async def get(self, model, identity):
            return transfer

        async def scalar(self, statement):
            return patient

    authorized = asyncio.run(
        MigrationService(Session()).authorize_transfer(
            transfer.id, "patient-1", "patient-consent-reference"
        )
    )
    assert authorized.state == MigrationState.PATIENT_AUTHORIZED.value


def test_patient_cannot_authorize_another_patient_transfer():
    transfer = TransferRequest(
        id=uuid4(),
        health_id="INOD000001",
        source_repository_id=uuid4(),
        destination_repository_id=uuid4(),
        requested_by="admin-1",
        purpose="Migration",
        scope="All records",
        state=MigrationState.REQUESTED.value,
    )
    patient = PatientIdentity(
        display_health_id="INOD000001",
        issuing_jurisdiction="IN",
        given_name="Patient",
        family_name="One",
        date_of_birth=datetime(1990, 1, 1).date(),
        owner_subject="patient-1",
    )

    class Session(EmptySession):
        async def get(self, model, identity):
            return transfer

        async def scalar(self, statement):
            return patient

    with pytest.raises(ValueError, match="does not belong"):
        asyncio.run(
            MigrationService(Session()).authorize_transfer(
                transfer.id, "patient-2", "patient-consent-reference"
            )
        )
