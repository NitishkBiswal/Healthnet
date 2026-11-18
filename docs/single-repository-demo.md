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

## Patient consent and revocation

The Patient Portal lists consent grants with provider ID, purpose, scopes, expiry and current status. Patients can revoke an active grant from the same screen. The authenticated DELETE endpoint verifies that the caller owns the Health ID attached to the consent, marks the grant REVOKED with a server-side timestamp, and commits the change. Longitudinal access checks query only ACTIVE, currently valid consent on every request, so a revoked grant stops authorizing subsequent access. Revocation does not erase clinical records or historical audit information.

## Migration model

A repository move is a patient-directed, controlled custody migration:

1. The patient opens **Transfer repository** in the Patient Portal, chooses an available destination and supplies a reason (minimum 10 characters).
2. HealthNet records the current repository as the source and the selected repository as the destination. The patient reviews and explicitly authorizes the request.
3. After two successful transfers for the same Health ID, every subsequent transfer is placed in **PENDING_AUDITOR_REVIEW** after patient authorization. An Auditor must approve it; rejection prevents execution.
4. An Admin sees patient-authorized requests in the transfer queue and runs the verified transfer.
5. HealthNet exports the patient's FHIR resources from the current source, imports them into the destination, reads them back and verifies the package hash.
6. Only after successful verification does HealthNet deactivate the old Record Locator and activate the destination locator. The permanent Health ID remains unchanged.
7. The old repository's custody period is closed and retained in history; the previous clinical copy is retained for audit/retention, not automatically deleted.

The same transfer service supports repeated moves (for example Odisha -> Karnataka -> West Bengal). Each new move uses the then-current ACTIVE Record Locator as its source. HealthNet stores locator/custody metadata; clinical FHIR payloads remain in repositories. The application's normal record access and ingestion paths resolve only the ACTIVE locator. The old HAPI endpoint is not independently made read-only by this classroom prototype, so direct access to an old endpoint must be treated as an infrastructure/admin-only operation.

## Demo data

Run from the repository root after Docker, migrations and Keycloak are running:

    .\\backend\\.venv\\Scripts\\python.exe .\\scripts\\seed-single-repository-demo.py

The seed creates Health ID INOD000100 for Aarav Sharma, Odisha as the current repository, demo Provider ID PRV-IN-000001, and Patient/Encounter/Condition/Observation/MedicationRequest FHIR data. Kolkata and Karnataka are registered as independent migration destinations.

The Docker demo provisions three HAPI FHIR services: Odisha on `http://localhost:8090/fhir`, Kolkata on `http://localhost:8091/fhir`, and Karnataka on `http://localhost:8092/fhir`. Each uses its own PostgreSQL database (`hapi_fhir_db`, `hapi_fhir_kolkata_db`, and `hapi_fhir_karnataka_db`). The compose file includes an idempotent Karnataka database initializer so an existing PostgreSQL volume is supported. The seed script registers all three repositories. Migration therefore performs a real cross-HAPI, cross-database FHIR export/import, destination read-back and hash verification. If the backend itself runs inside Docker, set `KOLKATA_HAPI_FHIR_BASE_URL` and `KARNATAKA_HAPI_FHIR_BASE_URL` to the corresponding Compose service URLs; the defaults assume the backend/seed script runs on the host.

## Demo walkthrough

1. Start Docker with `docker compose -f infrastructure/docker-compose.yml up -d`. The Compose `karnataka-db-init` service creates the Karnataka FHIR database even when you already have an existing PostgreSQL volume; `init-databases.sql` creates all FHIR databases on a fresh volume.
2. Wait until both HAPI services are healthy, then run Alembic migrations.
3. Start the backend and frontend.
4. Run `scripts/seed-single-repository-demo.py`.
5. Login as `testpatient`, show Health ID `INOD000100` and the current Odisha repository. Open **Transfer repository**, choose Karnataka, enter a clear reason (for example, permanent relocation), submit the request and authorize it.
6. Login as `testdoctor`, note Provider ID `PRV-IN-000001`, and confirm the patient is not visible before consent.
7. Login as `testpatient`, grant the doctor clinical consent, then return to the Doctor Portal and open the longitudinal record.
8. Return to the Patient Portal and click **Revoke access**. Refresh the Doctor Portal and show that the patient is no longer authorized; a direct longitudinal-view request should be denied.
9. In Admin, refresh the **Patient-initiated repository transfer queue**. Run the verified transfer after patient authorization.
10. Show the manifest resource count and `VALID` destination verification. Confirm the current Record Locator now points to Karnataka while Health ID remains `INOD000100`; the destination resources are in the separate Karnataka HAPI/PostgreSQL database.
11. For a second transfer, move Karnataka -> Kolkata. After two completed moves, request another transfer: after patient authorization it must appear in the Auditor Portal. Approve or reject it as Auditor before Admin can execute it.

## Core rule

One Health ID, one current authoritative repository, controlled migration when custody changes.


## Repository database architecture

For a convincing multi-repository demonstration, run one FHIR server per repository, each backed by its own PostgreSQL database (for example, Odisha HAPI -> `hapi_odisha_db`, Kolkata HAPI -> `hapi_kolkata_db`). The central HealthNet database stores identities, consent, custody history and the active Record Locator; it should not store the clinical payloads. Configure each repository's `base_url` to its own HAPI endpoint. During transfer, HealthNet exports FHIR resources from the source, imports them idempotently into the destination, reads them back and verifies the content hash before switching the active locator. Keep the source read-only for a defined retention period and preserve provenance/audit history.

Do not copy PostgreSQL data directories or raw HAPI database tables between repositories: that couples repositories to HAPI/PostgreSQL internals and risks inconsistent indexes, references and server metadata. Use FHIR resource export/import for the clinical data plane. For a small classroom demo, separate databases on one PostgreSQL container are acceptable; for stronger isolation, use separate PostgreSQL instances as well. The current default seed still uses one shared HAPI endpoint and must be described as a logical/in-place transfer, not a physical cross-database copy.


## Indian EHR Standards and ABDM alignment

HealthNet's interoperability target is the Ministry of Health and Family Welfare's **EHR Standards for India (2016)** together with the **NRCeS ABDM FHIR Implementation Guide v6.5.0**, based on HL7 FHIR R4. The guide defines Indian-context profiles for Patient, Encounter, Condition, Observation, DiagnosticReport, MedicationRequest, DocumentReference, Composition-based clinical documents and DocumentBundle.

Implementation choices in this prototype:

- **Patient identity:** HealthNet Health ID remains the application's stable internal identifier. The optional Aadhaar number is stored separately in the identity vault, encrypted with authenticated AES-256-GCM at application level; only a last-four hint is retained alongside ciphertext. Registration performs only a 12-digit format check. There is no UIDAI verification, OTP, biometric, eKYC, or claim that the Aadhaar belongs to the patient. Aadhaar is not emitted in provider-facing API responses or copied into clinical FHIR resources.
- **Aadhaar vs ABHA:** Aadhaar is a government identity identifier; ABHA is a distinct digital health identifier under ABDM. This prototype does not create, verify, or claim an ABHA number. A future ABHA field/integration must remain separate.
- **FHIR exchange:** Clinical resources use FHIR R4 and the canonical ABDM Patient profile is attached to HealthNet-created canonical Patient resources. Clinical artifacts should use the corresponding ABDM profiles (for example Condition, Encounter, Observation, DiagnosticReportLab/Imaging, MedicationRequest and DocumentReference). For exchangeable clinical documents, use ABDM Composition profiles and DocumentBundle rather than sending isolated unstructured objects.
- **Record integrity:** Clinical record ingestion treats records as immutable. An identical retry is idempotent; a changed clinical payload with the same resource ID is rejected and must be submitted as a new record, preserving the original and its audit trail.
- **Terminology:** Use SNOMED CT for clinical concepts, LOINC for laboratory tests and measurements, and applicable WHO ICD classification for reporting. Preserve coding system, code, display, units and reference links; do not rely on free-text labels alone.
- **Consent and audit:** Existing consent checks gate provider access and revocation blocks subsequent requests. Access and migration operations are recorded with provenance/audit information. ABDM's HIU/HIP consent-mediated exchange model is the target design.
- **Privacy:** Aadhaar is deliberately kept out of clinical repositories. Configure a dedicated AADHAAR_ENCRYPTION_KEY secret in each backend environment; the local SECRET_KEY fallback exists only to keep development setup runnable. Keep the key outside source control and rotate it with a planned re-encryption procedure.

### Conformance boundary

This is an **ABDM-aligned prototype**, not an ABDM-certified or sandbox-integrated application. Merely tagging a FHIR resource with a profile URL does not prove conformance. Before claiming full compliance, validate every exchanged resource/document against the selected NRCeS package and terminology value sets, implement the ABDM HIP/HIU and consent-manager gateway workflows, complete sandbox onboarding and required security assessment, and verify applicable privacy/legal obligations. The ABDM guide itself describes FHIR R4 as its base and defines minimum conformance requirements; the MoHFW EHR Standards provide broader recommendations for identifiers, clinical terminologies, exchange and security.

Official references:
- MoHFW, EHR Standards for India: https://www.mohfw.gov.in/sites/default/files/EMR-EHR_Standards_for_India_as_notified_by_MOHFW_2016_0.pdf
- NRCeS, EHR Standards for India: https://www.nrces.in/standards/ehr-standards-for-india
- NRCeS, ABDM FHIR R4 Implementation Guide v6.5.0: https://nrces.in/ndhm/fhir/r4/
- ABDM HIP/HIU guidelines: https://abdm.gov.in/strapicms/uploads/HIP_HIU_Guidelines_f85df336ec.pdf


## CSV and Excel legacy-record import

The Admin Portal includes **Import existing medical records (CSV / Excel)**. The backend accepts .csv, .xlsx and .xlsm uploads up to 10 MB and 5,000 rows. Each row is independently validated and routed through the patient's active Record Locator; a row for an unknown Health ID, missing repository, invalid date, duplicate resource ID or unsupported type is rejected without stopping other rows.

Supported normalized record types in this first iteration:

- CONDITION -> ABDM-profiled FHIR R4 Condition.
- OBSERVATION -> ABDM-profiled FHIR R4 Observation.

Required columns: health_id, record_type, record_id, display, recorded_at. Optional columns: code, code_system, status, value, unit, source_hospital, is_chronic, emergency_relevant. The downloadable template is at frontend/public/medical-record-import-template.csv. Use ISO dates/datetimes. Use stable, unique resource IDs per patient. A numeric Observation value is converted to a FHIR Quantity; a non-numeric value is stored as a string. Imported Conditions are marked unconfirmed because the source file is not independently verified. The source hospital, row number and upload file SHA-256 are retained in provenance/audit metadata.

**Permissions:** Admin can import. Auditor receives read-only access to the imported-record audit feed and cannot write or alter clinical resources. This initial feature does not yet import PDF, DICOM, HL7 messages, prescriptions or arbitrary Excel layouts; source systems must map their export columns to the template first.

**Emergency summary:** Only a Condition row explicitly marked with both is_chronic=TRUE and emergency_relevant=TRUE is added to the patient's emergency conditions field. This is an administrative import flag, not automated medical triage. Review the emergency summary for accuracy and completeness.

**Retention:** HealthNet does not automatically delete clinical records after six months. Old records may still be needed for diagnosis, continuity of care, medico-legal purposes or future treatment. In particular, chronic conditions such as diabetes, cardiovascular disease and other long-term complications should remain in the longitudinal record and, when clinically appropriate, the emergency summary. A production retention/archive policy must be configured against applicable law, record type and hospital policy; do not equate six months of inactivity with permission to delete.
