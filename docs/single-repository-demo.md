# Single-authoritative-repository demo

HealthNet now treats the patient's clinical record as being held by one current authoritative repository.

## Runtime model

Patient Health ID -> Record Locator -> Current repository only -> FHIR repository -> complete clinical record

A doctor does not scan every jurisdictional repository. After authentication, provider trust, consent and policy checks, HealthNet resolves the patient's current repository and queries that repository only.

The permanent Health ID does not change when the patient moves.

## Hospital record ingestion

A trusted provider can simulate a hospital submission from the **Hospital Integration Demo** linked in the Doctor Portal. The backend endpoint is:

    POST /api/v1/fhir/patients/{health_id}/records

The caller must be authenticated and linked to an active trusted HealthNet provider (or use an admin/system account for controlled demo setup). The caller cannot submit a repository URL. HealthNet resolves the patient's active Record Locator, validates the Health ID and patient reference, then writes the FHIR resource to that repository using an idempotent PUT.

Example Observation payload:

    {
      "resourceType": "Observation",
      "status": "final",
      "code": { "text": "Blood pressure" },
      "subject": { "reference": "Patient/INOD000100" },
      "effectiveDateTime": "2026-10-09T10:00:00Z",
      "valueQuantity": {
        "value": 128,
        "unit": "mmHg",
        "system": "http://unitsofmeasure.org",
        "code": "mm[Hg]"
      }
    }

For this prototype, the FHIR Patient resource uses the Health ID as its FHIR resource ID and carries the identifier system `urn:healthnet:health-id`. Clinical resources must reference `Patient/{health_id}`. A production hospital connector would map its local patient identifiers to HealthNet's canonical Health ID and preserve signed sender identity and provenance.

Patient registration now selects an online/degraded repository, preferring the issuing jurisdiction, and creates the active Record Locator and custody history in the same database transaction. Registration returns a clear service-unavailable error if no repository is available.

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

The local demo intentionally uses the same HAPI FHIR endpoint for both logical repositories so it does not require multiple HAPI containers. Migration still performs export, idempotent upsert, read-back validation and hash verification, but because both logical repositories share one endpoint it is an in-place demo transfer, not physical isolation. The manifest reports `VALID_SHARED_ENDPOINT`. For a demonstration of physical copying, configure the destination repository with a separate HAPI FHIR endpoint. A production deployment must use separate repository endpoints and secure service-to-service authentication.

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
