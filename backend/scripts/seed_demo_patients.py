"""Seed four local-only HealthNet demo patients and an import-ready CSV.

Run from the backend directory after PostgreSQL, Keycloak, and the HealthNet
schema migrations are ready:
    python -m scripts.seed_demo_patients

The script is idempotent. It creates two patients assigned to IN-KA and two
assigned to IN-OD, links each identity to its Keycloak subject, and writes
frontend/public/demo-medical-records.csv for the Admin medical-record importer.
Never use these demo credentials or records in a production environment.
"""
from __future__ import annotations

import asyncio
import csv
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker, close_db, init_db
from app.identity.models import PatientIdentity
from app.identity.schemas import PatientRegistrationRequest
from app.identity.service import IdentityService
from app.repository.models import Repository


DEMO_PASSWORD = "PatientDemo!2026"
PATIENTS = [
    {"username": "testpatient1", "given_name": "Aditi", "family_name": "Rao", "dob": date(1998, 4, 12), "jurisdiction": "IN-KA", "sex": "female"},
    {"username": "testpatient2", "given_name": "Rohan", "family_name": "Kulkarni", "dob": date(1989, 8, 23), "jurisdiction": "IN-KA", "sex": "male"},
    {"username": "testpatient3", "given_name": "Ananya", "family_name": "Das", "dob": date(1995, 2, 7), "jurisdiction": "IN-OD", "sex": "female"},
    {"username": "testpatient4", "given_name": "Arjun", "family_name": "Mohanty", "dob": date(1986, 11, 19), "jurisdiction": "IN-OD", "sex": "male"},
]

RECORDS = [
    ("CONDITION", "condition", "Type 2 diabetes mellitus", "44054006", "active", "", "", True, True),
    ("OBSERVATION", "observation", "Blood glucose", "2339-0", "final", "126", "mg/dL", False, False),
    ("OBSERVATION", "observation", "Blood pressure systolic", "8480-6", "final", "128", "mmHg", False, False),
    ("CONDITION", "condition", "Essential hypertension", "38341003", "active", "", "", True, True),
]


async def keycloak_admin_token(client: httpx.AsyncClient) -> str:
    response = await client.post(
        f"{settings.KEYCLOAK_URL.rstrip('/')}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": settings.KEYCLOAK_ADMIN_USERNAME,
            "password": settings.KEYCLOAK_ADMIN_PASSWORD,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def ensure_keycloak_patient(client: httpx.AsyncClient, headers: dict[str, str], item: dict[str, Any]) -> str:
    base = f"{settings.KEYCLOAK_URL.rstrip('/')}/admin/realms/{settings.KEYCLOAK_REALM}"
    response = await client.get(
        f"{base}/users",
        params={"username": item["username"], "exact": "true"},
        headers=headers,
    )
    response.raise_for_status()
    users = response.json()
    if users:
        user_id = users[0]["id"]
    else:
        created = await client.post(
            f"{base}/users",
            headers=headers,
            json={
                "username": item["username"],
                "enabled": True,
                "email": f'{item["username"]}@healthnet.dev',
                "emailVerified": True,
                "firstName": item["given_name"],
                "lastName": item["family_name"],
                "credentials": [{"type": "password", "value": DEMO_PASSWORD, "temporary": False}],
            },
        )
        if created.status_code not in (201, 409):
            created.raise_for_status()
        lookup = await client.get(
            f"{base}/users",
            params={"username": item["username"], "exact": "true"},
            headers=headers,
        )
        lookup.raise_for_status()
        found = lookup.json()
        if not found:
            raise RuntimeError(f"Keycloak did not return the newly created user {item['username']}")
        user_id = found[0]["id"]

    reset_password = await client.put(
        f"{base}/users/{user_id}/reset-password",
        headers=headers,
        json={"type": "password", "value": DEMO_PASSWORD, "temporary": False},
    )
    if reset_password.status_code not in (204, 409):
        reset_password.raise_for_status()

    role_response = await client.get(f"{base}/roles/patient", headers=headers)
    role_response.raise_for_status()
    mapping = await client.post(
        f"{base}/users/{user_id}/role-mappings/realm",
        headers=headers,
        json=[role_response.json()],
    )
    if mapping.status_code not in (204, 409):
        mapping.raise_for_status()
    return user_id


def write_demo_csv(rows: list[dict[str, str]]) -> Path:
    output = Path(__file__).resolve().parents[2] / "frontend" / "public" / "demo-medical-records.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "health_id", "record_type", "record_id", "display", "code", "code_system",
        "status", "recorded_at", "value", "unit", "source_hospital",
        "is_chronic", "emergency_relevant",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for patient in rows:
            for index, record in enumerate(RECORDS, start=1):
                kind, prefix, display, code, status, value, unit, chronic, emergency = record
                writer.writerow({
                    "health_id": patient["health_id"],
                    "record_type": kind,
                    "record_id": f'{patient["username"]}-{prefix}-{index:02d}',
                    "display": display,
                    "code": code,
                    "code_system": "http://loinc.org" if kind == "OBSERVATION" else "http://snomed.info/sct",
                    "status": status,
                    "recorded_at": f'2025-{(index % 12) + 1:02d}-15',
                    "value": value,
                    "unit": unit,
                    "source_hospital": "HealthNet Demo Hospital",
                    "is_chronic": str(chronic).upper(),
                    "emergency_relevant": str(emergency).upper(),
                })
    return output


async def main() -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        token = await keycloak_admin_token(client)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        subjects: dict[str, str] = {}
        for item in PATIENTS:
            subjects[item["username"]] = await ensure_keycloak_patient(client, headers, item)

    await init_db()
    assert async_session_maker is not None
    seeded: list[dict[str, str]] = []
    try:
        async with async_session_maker() as session:
            for item in PATIENTS:
                subject = subjects[item["username"]]
                patient = await session.scalar(
                    select(PatientIdentity).where(PatientIdentity.owner_subject == subject)
                )
                if patient is None:
                    repository = await session.scalar(
                        select(Repository).where(
                            Repository.jurisdiction == item["jurisdiction"],
                            Repository.status.in_(["ONLINE", "DEGRADED"]),
                        ).limit(1)
                    )
                    if repository is None:
                        raise RuntimeError(
                            f'No ONLINE/DEGRADED repository configured for {item["jurisdiction"]}. '
                            "Check repository jurisdiction values and HAPI configuration."
                        )
                    request = PatientRegistrationRequest(
                        given_name=item["given_name"],
                        family_name=item["family_name"],
                        date_of_birth=item["dob"],
                        sex=item["sex"],
                        email=f'{item["username"]}@healthnet.dev',
                        issuing_jurisdiction=item["jurisdiction"],
                    )
                    outcome, patient, matches, _review = await IdentityService(session).register_patient(
                        request, requesting_subject=subject
                    )
                    if outcome != "REGISTERED" or patient is None:
                        raise RuntimeError(
                            f'{item["username"]}: expected REGISTERED, got {outcome}; '
                            f"possible identity matches: {[match.patient.display_health_id for match in matches]}"
                        )
                    await session.commit()
                seeded.append({
                    "username": item["username"],
                    "given_name": item["given_name"],
                    "family_name": item["family_name"],
                    "jurisdiction": item["jurisdiction"],
                    "health_id": patient.display_health_id,
                })
    finally:
        await close_db()

    csv_path = write_demo_csv(seeded)
    print("\nHealthNet demo patients are ready:")
    for item in seeded:
        print(f'  {item["username"]:<14} {item["given_name"]} {item["family_name"]:<14} {item["jurisdiction"]}  {item["health_id"]}')
    print(f"\nPatient login password (local demo only): {DEMO_PASSWORD}")
    print(f"Import file created: {csv_path}")
    print("Open Admin Portal > Medical Records Import and upload demo-medical-records.csv.")


if __name__ == "__main__":
    asyncio.run(main())
