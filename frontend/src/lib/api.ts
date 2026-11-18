import { getAccessToken } from "@/lib/auth";

export type ServiceStatus = "healthy" | "degraded" | "unhealthy";
export interface ServiceHealth { service: string; status: ServiceStatus; latency_ms: number | null; details?: Record<string, unknown> | null; }
export interface AggregateHealthResponse { status: ServiceStatus; version: string; services: ServiceHealth[]; }
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "").replace(/\/api\/v1$/, "") + "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const response = await fetch(API_BASE_URL + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
      ...(options?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.text();
    let message = body || "HTTP " + response.status;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      if (parsed.detail) message = parsed.detail;
    } catch {}
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function fetchHealth() { return request<AggregateHealthResponse>("/health"); }

export interface Patient {
  id?: string; display_health_id: string; issuing_jurisdiction: string; given_name: string; family_name: string;
  date_of_birth: string; sex?: string; phone?: string; email?: string; address?: string; status: string;
}
export interface PatientRegistration {
  given_name: string; family_name: string; date_of_birth: string; sex?: string; phone?: string; email?: string;
  address?: string; issuing_jurisdiction: string;
  identifiers?: { identifier_type: string; identifier_value: string; issuing_authority?: string }[];
}
export interface MatchCandidate { patient_id: string; health_id: string; confidence: number; band: string; }
export interface RegistrationResult { outcome: string; patient?: Patient; matches: MatchCandidate[]; duplicate_review_id?: string; }
export interface DuplicateReview {
  id: string; candidate_patient_id: string; confidence: number; status: string; reviewer_note?: string;
  proposed_given_name: string; proposed_family_name: string; proposed_date_of_birth: string; proposed_sex?: string;
  proposed_phone?: string; proposed_email?: string; proposed_issuing_jurisdiction?: string;
  proposed_identifiers?: { identifier_type: string; identifier_value: string; issuing_authority?: string }[];
  created_at: string; reviewed_at?: string;
}
export interface Repository { id: string; code: string; name: string; jurisdiction: string; base_url: string; status: string; description?: string; }
export interface Consent {
  id: string; health_id: string; grantee_type: string; grantee_id: string; purpose: string; scopes: string[];
  status: string; valid_from: string; valid_until?: string; revoked_at?: string; reason?: string;
}
export interface AuthorizedPatient {
  health_id: string; given_name: string; family_name: string; consent_id: string; purpose: string;
  scopes: string[]; valid_from: string; valid_until?: string;
}
export interface Provider {
  id: string; external_id: string; given_name: string; family_name: string; license_number: string;
  jurisdiction: string; trust_status: string; keycloak_subject?: string;
}
export interface Principal {
  subject: string; email?: string; roles: string[]; provider_id?: string | null;
  provider_name?: string | null; provider_status?: string | null;
}
export interface AuditEvent { id: string; event_type: string; health_id?: string; actor_id: string; action: string; payload: string; event_hash: string; created_at: string; }
export interface Custody { id: string; health_id: string; repository_id: string; resource_types: string[]; custody_start: string; custody_end?: string; }
export interface Transfer { id: string; health_id: string; source_repository_id: string; destination_repository_id: string; purpose: string; scope: string; state: string; authorization_reference?: string; package_hash?: string; error_message?: string; created_at: string; updated_at: string; }
export interface EmergencyProfile {
  health_id: string;
  blood_group?: string | null;
  allergies: string[];
  medications: string[];
  conditions: string[];
  emergency_contacts: string[];
  updated_at?: string | null;
}
export interface PatientNotification {
  id: string; health_id: string; event_type: string; message: string;
  created_at: string; read_at?: string | null;
}
export interface BreakGlassGrant {
  event_id: string; health_id: string; authorization_token: string; expires_at: string;
}
export interface ProvenanceResource {
  resourceType: "Provenance"; id: string; target: { reference: string }[];
  recorded: string; agent: Record<string, unknown>[];
  activity: { coding?: { display?: string }[] };
  entity: Record<string, unknown>[];
}
export interface Jurisdiction { id: string; code: string; name: string; active: boolean; }
export interface PolicyRule {
  id: string; jurisdiction_id: string; name: string; purpose: string; scope: string;
  effect: "ALLOW" | "DENY"; description?: string | null; active: boolean;
}
export interface LongitudinalRecord {
  repository: string; resource_type: string; resource: Record<string, unknown>;
}
export interface LongitudinalResult {
  health_id: string; completeness: "COMPLETE" | "PARTIAL" | "UNAVAILABLE";
  records: LongitudinalRecord[]; repositories_checked: number;
  repositories_available: number; errors: string[];
}

export const api = {
  currentPrincipal: () => request<Principal>("/authorization/me"),
  patient: (healthId: string) => request<Patient>("/identity/" + encodeURIComponent(healthId)),
  myPatient: () => request<Patient>("/identity/me"),
  registerPatient: (body: PatientRegistration) => request<RegistrationResult>("/identity/register", { method: "POST", body: JSON.stringify(body) }),
  myDuplicateReviews: () => request<DuplicateReview[]>("/identity/duplicate-reviews/mine"),
  duplicateReviews: () => request<DuplicateReview[]>("/identity/duplicate-reviews"),
  decideDuplicateReview: (id: string, decision: "APPROVED_DUPLICATE" | "REJECTED", reviewer_note?: string) =>
    request<DuplicateReview>("/identity/duplicate-reviews/" + encodeURIComponent(id) + "/decision", { method: "POST", body: JSON.stringify({ decision, reviewer_note }) }),
  createConsent: (body: { health_id: string; grantee_type: string; grantee_id: string; purpose: string; scopes: string[]; valid_from: string; valid_until?: string; reason?: string }) =>
    request<Consent>("/consent/consents", { method: "POST", body: JSON.stringify(body) }),
  revokeConsent: (id: string) => request<Consent>("/consent/consents/" + encodeURIComponent(id), { method: "DELETE" }),
  consents: (healthId: string, offset = 0, limit = 50) =>
    request<Consent[]>(`/consent/patients/${encodeURIComponent(healthId)}/consents?offset=${offset}&limit=${limit}`),
  authorizedPatients: (offset = 0, limit = 50) =>
    request<AuthorizedPatient[]>(`/consent/authorized-patients?offset=${offset}&limit=${limit}`),
  providers: () => request<Provider[]>("/provider-trust/providers"),
  onboardProvider: (body: { username:string; email:string; initial_password:string; given_name:string; family_name:string; license_number:string; jurisdiction:string }) =>
    request<{ provider:Provider; username:string; message:string }>("/provider-trust/providers/onboard",{method:"POST",body:JSON.stringify(body)}),
  createProvider: (body: { external_id: string; given_name: string; family_name: string; license_number: string; jurisdiction: string; keycloak_subject?: string }) =>
    request<Provider>("/provider-trust/providers", { method: "POST", body: JSON.stringify(body) }),
  emergency: (healthId: string) => request<EmergencyProfile>("/emergency/patients/" + encodeURIComponent(healthId) + "/emergency-profile"),
  saveEmergency: (healthId: string, body: Omit<EmergencyProfile, "health_id" | "updated_at">) =>
    request<EmergencyProfile>("/emergency/patients/" + encodeURIComponent(healthId) + "/emergency-profile", { method: "PUT", body: JSON.stringify(body) }),
  notifications: (healthId: string) =>
    request<PatientNotification[]>("/emergency/patients/" + encodeURIComponent(healthId) + "/notifications"),
  breakGlass: (healthId: string, reason: string) =>
    request<BreakGlassGrant>("/emergency/patients/" + encodeURIComponent(healthId) + "/break-glass", {
      method: "POST", body: JSON.stringify({ reason, tier: "TIER_1" }),
    }),
  longitudinal: (
    healthId: string,
    purpose = "TREATMENT",
    scope = "clinical",
    options: { from_date?: string; to_date?: string; resource_types?: string[]; breakGlassToken?: string } = {},
  ) => request<LongitudinalResult>("/longitudinal/patients/longitudinal-view", {
    method: "POST",
    body: JSON.stringify({
      health_id: healthId, purpose, scope,
      from_date: options.from_date || undefined,
      to_date: options.to_date || undefined,
      resource_types: options.resource_types || [],
    }),
    headers: options.breakGlassToken ? { "X-Break-Glass-Token": options.breakGlassToken } : {},
  }),
  repositories: (offset = 0, limit = 50) =>
    request<Repository[]>(`/repository/repositories?offset=${offset}&limit=${limit}`),
  audits: (healthId: string, offset = 0, limit = 50) =>
    request<AuditEvent[]>(`/audit/patient/${encodeURIComponent(healthId)}?offset=${offset}&limit=${limit}`),
  provenance: (healthId: string) =>
    request<ProvenanceResource[]>("/provenance/provenance/" + encodeURIComponent(healthId)),
  jurisdictions: () => request<Jurisdiction[]>("/jurisdiction-policy/policy/jurisdictions"),
  policyRules: () => request<PolicyRule[]>("/jurisdiction-policy/policy/rules"),
  addPolicyRule: (body: Omit<PolicyRule, "id" | "jurisdiction_id" | "active"> & { jurisdiction_code: string }) =>
    request<PolicyRule>("/jurisdiction-policy/policy/rules", { method: "POST", body: JSON.stringify(body) }),
  deactivatePolicyRule: (id: string) =>
    request<PolicyRule>("/jurisdiction-policy/policy/rules/" + encodeURIComponent(id), { method: "DELETE" }),
  verifyLedger: () => request<{ valid: boolean; entries_checked: number }>("/trust-ledger/ledger/verify"),
  createFHIRResource: (resourceType: string, resource: Record<string, unknown>) =>
    request<Record<string, unknown>>("/fhir/" + encodeURIComponent(resourceType), { method: "POST", body: JSON.stringify(resource) }),
  changeRepository: (healthId: string, repositoryId: string) =>
    request<Custody>("/repository/patients/" + encodeURIComponent(healthId) + "/ehr-custody", { method: "PUT", body: JSON.stringify({ repository_id: repositoryId, resource_types: ["FHIR"] }) }),
  createTransfer: (body: { health_id: string; source_repository_id: string; destination_repository_id: string; purpose: string; scope: string }) =>
    request<Transfer>("/migration/transfer-requests", { method: "POST", body: JSON.stringify(body) }),
  authorizeTransfer: (id: string, authorization_reference: string) =>
    request<Transfer>("/migration/transfer-authorizations/" + encodeURIComponent(id), { method: "POST", body: JSON.stringify({ authorization_reference }) }),
  issueTransferToken: (id: string) =>
    request<{ transfer_id: string; authorization_token: string; expires_at: string }>("/migration/transfers/" + encodeURIComponent(id) + "/issue-token", { method: "POST" }),
  executeTransfer: (id: string, authorization_token: string) =>
    request<{ id: string; resource_count: number; package_hash: string; validation_status: string }>("/migration/transfers/" + encodeURIComponent(id) + "/execute", { method: "POST", body: JSON.stringify({ authorization_token }) }),
  transferStatus: (id: string) => request<Transfer>("/migration/transfers/" + encodeURIComponent(id) + "/status"),
};
