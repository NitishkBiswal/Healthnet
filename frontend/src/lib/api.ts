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
export interface Transfer { id: string; health_id: string; source_repository_id: string; destination_repository_id: string; purpose: string; scope: string; state: string; authorization_reference?: string; package_hash?: string; error_message?: string; created_at: string; updated_at: string; }

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
  consents: (healthId: string) => request<Consent[]>("/consent/patients/" + encodeURIComponent(healthId) + "/consents"),
  authorizedPatients: () => request<AuthorizedPatient[]>("/consent/authorized-patients"),
  providers: () => request<Provider[]>("/provider-trust/providers"),
  createProvider: (body: { external_id: string; given_name: string; family_name: string; license_number: string; jurisdiction: string; keycloak_subject?: string }) =>
    request<Provider>("/provider-trust/providers", { method: "POST", body: JSON.stringify(body) }),
  emergency: (healthId: string) => request<Record<string, unknown>>("/emergency/patients/" + encodeURIComponent(healthId) + "/emergency-profile"),
  longitudinal: (healthId: string, purpose = "TREATMENT", scope = "clinical") =>
    request<Record<string, unknown>>("/longitudinal/patients/longitudinal-view", { method: "POST", body: JSON.stringify({ health_id: healthId, purpose, scope }) }),
  repositories: () => request<Repository[]>("/repository/repositories"),
  audits: (healthId: string) => request<AuditEvent[]>("/audit/patient/" + encodeURIComponent(healthId)),
  verifyLedger: () => request<{ valid: boolean; entries_checked: number }>("/trust-ledger/ledger/verify"),
  createTransfer: (body: { health_id: string; source_repository_id: string; destination_repository_id: string; purpose: string; scope: string }) =>
    request<Transfer>("/migration/transfer-requests", { method: "POST", body: JSON.stringify(body) }),
  transferStatus: (id: string) => request<Transfer>("/migration/transfers/" + id + "/status"),
};
