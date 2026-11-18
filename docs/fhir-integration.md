# FHIR Integration

## Integration pattern

The FastAPI backend orchestrates application workflows and communicates with HAPI FHIR over its REST API. HAPI FHIR R4 stores and serves clinical resources. The browser does not connect directly to a repository for normal application workflows.

## Local repository endpoints

| Demonstration repository | HAPI FHIR base URL | PostgreSQL database |
|---|---|---|
| Default / Odisha | http://localhost:8090/fhir | `hapi_fhir_db` |
| Kolkata | http://localhost:8091/fhir | `hapi_fhir_kolkata_db` |
| Karnataka | http://localhost:8092/fhir | `hapi_fhir_karnataka_db` |

These are separate HAPI instances with separate databases, provisioned by `infrastructure/docker-compose.yml`. The Karnataka database initializer is a one-shot container and normally exits after it has created/granted access to the database.

## Responsibilities

- **FastAPI:** user authentication and authorization, patient consent checks, repository-locator resolution, workflow orchestration, validation and audit/provenance integration.
- **HAPI FHIR:** FHIR R4 resource persistence and FHIR REST interactions.
- **PostgreSQL:** HealthNet application metadata and the individual databases backing Keycloak and HAPI FHIR.

## Repository selection and access

The HealthNet application resolves a patient's current active Record Locator before accessing their clinical resources. Provider access is gated by the application's trust/role and patient-consent checks. A revoked consent must not authorize subsequent protected record requests.

## Repository transfer demonstration

The transfer workflow uses FHIR resource exchange rather than copying PostgreSQL data directories or HAPI database tables. The backend exports the patient's resources from the source HAPI instance, imports them into the destination, reads them back and verifies the transfer package before switching the active locator. The previous repository's data is retained as historical demo data; the prototype does not provide a production-grade network isolation or retention enforcement layer.

## Scope and conformance

This project uses FHIR R4/HAPI FHIR as its interoperability foundation. It is an academic/demo prototype, not an ABDM-certified product or a completed ABDM sandbox integration. Profile tagging alone is not proof of conformance. Production use would require full profile/terminology validation, ABDM gateway and consent-manager integration, security assessment, privacy/legal review, operational controls and deployment hardening.
