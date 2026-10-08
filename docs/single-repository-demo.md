# Single-authoritative-repository demo

HealthNet now treats the patient's clinical record as being held by one current authoritative repository.

## Runtime model

Patient Health ID -> Record Locator -> Current repository only -> FHIR repository -> complete clinical record

A doctor does not scan every jurisdictional repository. After authentication, provider trust, consent and policy checks, HealthNet resolves the patient's current repository and queries that repository only.

The permanent Health ID does not change when the patient moves.

## Migration model

A repository move is a controlled custody migration:

1. Admin creates a migration request from the patient's current repository to the destination.
2. The patient authorizes the request.
3. Admin issues the transfer authorization token.
4. The migration control plane records validation, hashing, transfer and destination validation.
5. Source custody becomes inactive/read-only.
6. The destination becomes the patient's single ACTIVE Record Locator.
7. Historical EHR custody remains auditable.

HealthNet stores locator/custody metadata; clinical FHIR payloads remain in repositories.

## Demo data

Run from the repository root after Docker, migrations and Keycloak are running:

    .\\backend\\.venv\\Scripts\\python.exe .\\scripts\\seed-single-repository-demo.py

The seed creates Health ID INOD000100 for Aarav Sharma, Odisha as the current repository, demo Provider ID PRV-IN-000001, and Patient/Encounter/Condition/Observation/MedicationRequest FHIR data. Kolkata is also registered as a logical migration destination.

The local demo intentionally uses the existing HAPI FHIR endpoint for both logical repositories so it does not require the heavy three-HAPI setup used by the abandoned federation demo. A production deployment can give each repository its own FHIR endpoint.

## Demo walkthrough

1. Start Docker and run Alembic migrations.
2. Start the backend and frontend.
3. Run seed-single-repository-demo.py.
4. Login as testpatient and show INOD000100 plus the current Odisha repository.
5. Login as testdoctor, use Provider ID PRV-IN-000001, obtain patient consent, and request the longitudinal view.
6. In Admin, create a migration from IN-OD-FHIR to IN-WB-KOL-FHIR.
7. Login as testpatient and authorize the repository move.
8. Return to Admin and complete the validated migration.
9. The current Record Locator now points to Kolkata while the Health ID remains INOD000100.

## Core rule

One Health ID, one current authoritative repository, controlled migration when custody changes.
