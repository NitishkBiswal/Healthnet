# HealthNet Electronic Health Record controls

## Scope and official basis

This document records controls implemented for the current HealthNet application and distinguishes them from legal compliance claims. The project should be treated as an electronic health record (EHR) application: it identifies patients, stores consent and custody metadata, writes FHIR resources to a repository, retrieves longitudinal records, and maintains an audit ledger. HealthNet is not yet assumed to be a registered/regulated ABDM HIP or HIU; participant role and sectoral obligations must be confirmed before production enrollment.

Authoritative sources used:

- [Ayushman Bharat Digital Mission](https://abdm.gov.in/) — India national digital-health mission and participating entity context.
- [ABDM Sandbox FHIR model overview](https://sandbox.abdm.gov.in/docs/fhirmodeloverview) and [ABDM Consent Manager overview](https://sandbox.abdm.gov.in/docs/cmoverview) — FHIR R4 and purpose-specific consent, revoke, and audit flows.
- [NRCES standards](https://www.nrces.in/) — India-specific FHIR profiles and implementation resources.
- [HL7 FHIR R4.0.1](https://hl7.org/fhir/R4/) — base exchange representation used in ABDM flows.
- [Digital Personal Data Protection Act, 2023](https://www.indiacode.nic.in/bitstream/123456789/22031/1/a2023-15.pdf) and [MeitY DPDP materials](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa) — notice, lawful processing, security, correction, erasure, and accountable entity responsibilities.

Sources should be re-checked against the exact ABDM gateway/profile release and final notified DPDP rules at deployment time.

## Applicable controls implemented

- **FHIR R4 representation:** provider-created resources are validated as FHIR resources, must have `resourceType` matching the route, must identify the patient as `Patient/<Health ID>`, and must not provide a new resource ID.
- **Purpose-specific consent:** provider record creation requires an active trusted provider and active treatment consent whose scope covers the resource type (or `full`). Consent validity and revocation are enforced before access.
- **Patient-controlled revocation:** patients may revoke their consent with confirmation. Repeated revocation and missing consent are rejected distinctly. Revocation is committed transactionally and updates the authorization decision immediately.
- **Least privilege:** static roles remain separate from patient consent. Repository switching and repository administration require the ADMIN role. FHIR creation requires the PROVIDER role plus a trusted provider linkage and consent.
- **Repository validation:** a target repository is not made active until its FHIR metadata endpoint responds successfully. Active custody and locators are changed only after validation and are not deleted or copied.
- **Audit traceability:** consent revocation and repository changes are hash-chained audit events. FHIR creation is audited after successful external creation using only event type, patient, actor, action, resource type, repository ID, and returned resource ID. Clinical payloads and access tokens are not placed in audit payloads.
- **Integrity and error handling:** writes are transactional; target validation failures preserve existing custody; API failures use appropriate 400/403/404/409/502 responses; confirmation and success/error feedback are displayed in the UI.
- **Sensitive data handling:** credential-bearing values are not stored in repository records or added to audit events. Repository configuration uses the configured FHIR base URL and application credentials remain outside source control.

## Access, retention, archival, and deletion assumptions

- ABDM consent-management controls apply to an ABDM-consent-managed exchange, but do not replace the project owner's DPDP and sectoral obligations.
- No public ABDM overview establishes a universal EHR record retention duration or deletion SLA. No retention period is therefore invented here.
- Record deletion and archival policy must be chosen by the project Data Fiduciary from the DPDP Act/Rules, applicable clinical-establishment or professional rules, litigation/audit holds, contracts, and purpose of processing.
- Existing repository switching does not copy or delete existing FHIR resources. A separate, authorized migration/deletion workflow is required before records may be moved or destroyed.
- Secure deletion, key destruction, backup expiry, and retention enforcement remain deployment responsibilities. Configure database encryption-at-rest and TLS according to the selected deployment and competent-authority requirements; ABDM public overview material alone does not prescribe an application-specific database algorithm or key schedule.
- Consent data and audit evidence may need to be retained for investigation, reconciliation, or legal holds. That decision must be stated in the project's final data-retention schedule.

## Verification limitations

This implementation should not be described as “ABDM-compliant” or “DPDP-compliant” by itself. It implements a set of verified ABDM/DPDP-aligned controls, but full conformance requires role confirmation (HIP/HIU/consent manager), exact profile version validation, gateway onboarding, threat modeling, formal privacy and legal review, and deployment configuration evidence.
