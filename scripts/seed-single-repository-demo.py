"""Seed a complete single-authoritative-repository HealthNet demo.

Run from the repository root:
    .\\.venv\\Scripts\\python.exe scripts\\seed-single-repository-demo.py
"""

import asyncio
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings
from app.identity.models import PatientIdentity
from app.jurisdiction_policy.models import Jurisdiction
from app.provider_trust.models import Provider
from app.record_locator.models import RecordLocator
from app.repository.models import EHRCustody, Repository


HEALTH_ID = "INOD000100"
FHIR_BASE = settings.HAPI_FHIR_BASE_URL.rstrip("/")
KOLKATA_FHIR_BASE = os.getenv("KOLKATA_HAPI_FHIR_BASE_URL", "http://localhost:8091/fhir").rstrip("/")
KARNATAKA_FHIR_BASE = os.getenv("KARNATAKA_HAPI_FHIR_BASE_URL", "http://localhost:8092/fhir").rstrip("/")
PATIENT_NAME = ("Aarav", "Sharma")


async def keycloak_subject(username: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            f"{settings.KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": settings.KEYCLOAK_ADMIN_USERNAME,
                "password": settings.KEYCLOAK_ADMIN_PASSWORD,
            },
        )
        token_response.raise_for_status()
        token = token_response.json()["access_token"]
        response = await client.get(
            f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}/users",
            params={"username": username},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        users = response.json()
        if not users:
            raise RuntimeError(f"Keycloak user {username!r} was not found")
        return users[0]["id"]


async def put_fhir(resource: dict) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.put(
            f"{FHIR_BASE}/{resource['resourceType']}/{resource['id']}",
            json=resource,
            headers={"Content-Type": "application/fhir+json"},
        )
        response.raise_for_status()


async def seed_database(patient_subject: str, provider_subject: str) -> str:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        odisha = await session.scalar(
            select(Repository).where(Repository.code == "IN-OD-FHIR")
        )
        if odisha is None:
            odisha = Repository(
                code="IN-OD-FHIR",
                name="Odisha Health Records Repository",
                jurisdiction="IN-OD",
                base_url=FHIR_BASE,
                description="Demo authoritative FHIR repository for patients registered in Odisha.",
                status="ONLINE",
            )
            session.add(odisha)

        kolkata = await session.scalar(
            select(Repository).where(Repository.code == "IN-WB-KOL-FHIR")
        )
        if kolkata is None:
            kolkata = Repository(
                code="IN-WB-KOL-FHIR",
                name="Kolkata Health Records Repository",
                jurisdiction="IN-WB",
                base_url=KOLKATA_FHIR_BASE,
                description="Demo destination repository backed by its own HAPI FHIR service and PostgreSQL database.",
                status="ONLINE",
            )
            session.add(kolkata)
        else:
            kolkata.base_url = KOLKATA_FHIR_BASE
            kolkata.description = "Demo destination repository backed by its own HAPI FHIR service and PostgreSQL database."

        karnataka = await session.scalar(
            select(Repository).where(Repository.code == "IN-KA-BLR-FHIR")
        )
        if karnataka is None:
            karnataka = Repository(
                code="IN-KA-BLR-FHIR",
                name="Karnataka Health Records Repository",
                jurisdiction="IN-KA",
                base_url=KARNATAKA_FHIR_BASE,
                description="Demo destination repository backed by its own Karnataka HAPI FHIR service and PostgreSQL database.",
                status="ONLINE",
            )
            session.add(karnataka)
        else:
            karnataka.base_url = KARNATAKA_FHIR_BASE
            karnataka.description = "Demo destination repository backed by its own Karnataka HAPI FHIR service and PostgreSQL database."

        jurisdiction = await session.scalar(
            select(Jurisdiction).where(Jurisdiction.code == "IN-OD")
        )
        if jurisdiction is None:
            jurisdiction = Jurisdiction(code="IN-OD", name="Odisha", active=True)
            session.add(jurisdiction)

        patient = await session.scalar(
            select(PatientIdentity).where(PatientIdentity.owner_subject == patient_subject)
        )
        if patient is None:
            patient = await session.scalar(
                select(PatientIdentity).where(PatientIdentity.display_health_id == HEALTH_ID)
            )
        if patient is None:
            patient = PatientIdentity(
                id=uuid4(),
                display_health_id=HEALTH_ID,
                issuing_jurisdiction="IN-OD",
                given_name=PATIENT_NAME[0],
                family_name=PATIENT_NAME[1],
                date_of_birth=date(1998, 4, 12),
                sex="male",
                phone="+91-9000000100",
                email="aarav.sharma.demo@example.com",
                address="Bhubaneswar, Odisha, India",
                owner_subject=patient_subject,
                status="ACTIVE",
            )
            session.add(patient)
        else:
            patient.owner_subject = patient_subject
            patient.given_name, patient.family_name = PATIENT_NAME
            patient.issuing_jurisdiction = "IN-OD"

        provider = await session.scalar(
            select(Provider).where(Provider.external_id == "PRV-IN-000001")
        )
        if provider is None:
            provider = Provider(
                external_id="PRV-IN-000001",
                given_name="Ananya",
                family_name="Patnaik",
                license_number="DEMO-OD-0001",
                jurisdiction="IN-OD",
                trust_status="ACTIVE",
                keycloak_subject=provider_subject,
            )
            session.add(provider)
        else:
            provider.keycloak_subject = provider_subject
            provider.trust_status = "ACTIVE"

        await session.flush()

        await session.execute(
            RecordLocator.__table__.delete().where(
                RecordLocator.health_id == HEALTH_ID
            )
        )
        locator = RecordLocator(
            health_id=HEALTH_ID,
            repository_id=odisha.id,
            endpoint=FHIR_BASE,
            resource_types="Patient,Encounter,Condition,Observation,MedicationRequest",
            status="ACTIVE",
            notes="Demo: one authoritative repository for the patient's complete record.",
            last_verified_at=datetime.now(timezone.utc),
        )
        session.add(locator)

        await session.execute(
            EHRCustody.__table__.delete().where(EHRCustody.health_id == HEALTH_ID)
        )
        session.add(
            EHRCustody(
                health_id=HEALTH_ID,
                repository_id=odisha.id,
                resource_types="Patient,Encounter,Condition,Observation,MedicationRequest",
                custody_start=datetime.now(timezone.utc),
            )
        )

        await session.commit()
        seeded_health_id = patient.display_health_id

    await engine.dispose()
    return seeded_health_id


def fhir_resources(health_id: str) -> list[dict]:
    resources = [
    {
        "resourceType": "Patient",
        "id": HEALTH_ID,
        "meta": {"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient"]},
        "identifier": [{"system": "urn:healthnet:health-id", "value": health_id, "type": {"text": "HealthNet Health ID"}}],
        "name": [{"text": "Aarav Sharma", "family": "Sharma", "given": ["Aarav"]}],
        "gender": "male",
        "birthDate": "1998-04-12",
        "address": [{"city": "Bhubaneswar", "state": "Odisha", "country": "IN"}],
    },
    {
        "resourceType": "Encounter",
        "id": "demo-encounter-2026",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
        "subject": {"reference": f"Patient/{HEALTH_ID}"},
        "period": {"start": "2026-09-15T10:00:00Z", "end": "2026-09-15T10:30:00Z"},
    },
    {
        "resourceType": "Condition",
        "id": "demo-condition-hypertension",
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertensive disorder"}]},
        "subject": {"reference": f"Patient/{HEALTH_ID}"},
        "recordedDate": "2026-09-15",
    },
    {
        "resourceType": "Observation",
        "id": "demo-observation-bp",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{HEALTH_ID}"},
        "effectiveDateTime": "2026-09-15T10:15:00Z",
        "component": [
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]}, "valueQuantity": {"value": 138, "unit": "mmHg"}},
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]}, "valueQuantity": {"value": 88, "unit": "mmHg"}},
        ],
    },
    {
        "resourceType": "Observation",
        "id": "demo-observation-glucose",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "2345-7", "display": "Glucose"}]},
        "subject": {"reference": f"Patient/{HEALTH_ID}"},
        "effectiveDateTime": "2026-09-15T10:20:00Z",
        "valueQuantity": {"value": 126, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
    },
    {
        "resourceType": "Observation",
        "id": "demo-observation-hba1c",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c"}]},
        "subject": {"reference": f"Patient/{HEALTH_ID}"},
        "effectiveDateTime": "2026-09-15T10:25:00Z",
        "valueQuantity": {"value": 6.8, "unit": "%"},
    },
    {
        "resourceType": "MedicationRequest",
        "id": "demo-medication-metformin",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "860975", "display": "Metformin 500 MG"}]},
        "subject": {"reference": f"Patient/{HEALTH_ID}"},
        "dosageInstruction": [{"text": "500 mg twice daily with meals"}],
    },
    ]

    # Declare the intended ABDM R4 profile on each demo resource. The receiver
    # still needs formal profile/terminology validation before production exchange.
    for resource in resources:
        resource_type = resource["resourceType"]
        profile = f"https://nrces.in/ndhm/fhir/r4/StructureDefinition/{resource_type}"
        meta = resource.setdefault("meta", {})
        meta.setdefault("profile", [profile])

    return resources


async def main() -> None:
    patient_subject = await keycloak_subject("testpatient")
    provider_subject = await keycloak_subject("testdoctor")

    health_id = await seed_database(patient_subject, provider_subject)

    for resource in fhir_resources(health_id):
        await put_fhir(resource)

    print()
    print("HealthNet single-repository demo is ready.")
    print(f"Health ID: {health_id}")
    print("Current repository: IN-OD-FHIR (Odisha Health Records Repository)")
    print("Demo provider ID: PRV-IN-000001")
    print(f"Odisha FHIR endpoint: {FHIR_BASE}")
    print(f"Kolkata FHIR endpoint: {KOLKATA_FHIR_BASE}")
    print(f"Karnataka FHIR endpoint: {KARNATAKA_FHIR_BASE}")
    print()
    print("The doctor retrieves this patient's records from the current repository only.")
    print("The Admin Portal can request a move to IN-WB-KOL-FHIR, then the patient authorizes it.")
    print("Odisha, Kolkata and Karnataka use separate HAPI FHIR services and separate PostgreSQL databases.")


if __name__ == "__main__":
    asyncio.run(main())
