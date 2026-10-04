export type ServiceStatus = "healthy" | "degraded" | "unhealthy";
export interface ServiceHealth { service: string; status: ServiceStatus; latency_ms: number | null; details?: Record<string, unknown> | null; }
export interface AggregateHealthResponse { status: ServiceStatus; version: string; services: ServiceHealth[]; }
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "").replace(/\/api\/v1$/, "") + "/api/v1";
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("healthnet_token") : null;
  const response = await fetch(API_BASE_URL + path, { ...options, headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options?.headers ?? {}) }, cache: "no-store" });
  if (!response.ok) { const body = await response.text(); throw new Error(body || `HTTP ${response.status}`); }
  return response.json() as Promise<T>;
}
export function fetchHealth() { return request<AggregateHealthResponse>("/health"); }
export interface Patient { display_health_id: string; issuing_jurisdiction: string; given_name: string; family_name: string; date_of_birth: string; sex?: string; phone?: string; email?: string; address?: string; status: string; }
export interface Repository { id: string; code: string; name: string; jurisdiction: string; base_url: string; status: string; description?: string; }
export interface Consent { id: string; health_id: string; grantee_type: string; grantee_id: string; purpose: string; scopes: string[]; status: string; valid_from: string; valid_until?: string; revoked_at?: string; }
export interface AuditEvent { id: string; event_type: string; health_id?: string; actor_id: string; action: string; payload: string; event_hash: string; created_at: string; }
export interface Transfer { id: string; health_id: string; source_repository_id: string; destination_repository_id: string; purpose: string; scope: string; state: string; authorization_reference?: string; package_hash?: string; error_message?: string; created_at: string; updated_at: string; }
export const api = {
  patient: (healthId: string) => request<Patient>(`/identity/${encodeURIComponent(healthId)}`),
  consents: (healthId: string) => request<Consent[]>(`/consent/patients/${encodeURIComponent(healthId)}/consents`),
  emergency: (healthId: string) => request<Record<string, unknown>>(`/emergency/patients/${encodeURIComponent(healthId)}/emergency-profile`),
  longitudinal: (healthId: string, purpose = "TREATMENT", scope = "clinical") => request<Record<string, unknown>>("/longitudinal/patients/longitudinal-view", { method: "POST", body: JSON.stringify({ health_id: healthId, purpose, scope }) }),
  repositories: () => request<Repository[]>("/repository/repositories"),
  audits: (healthId: string) => request<AuditEvent[]>(`/audit/patient/${encodeURIComponent(healthId)}`),
  verifyLedger: () => request<{ valid: boolean; entries_checked: number }>("/trust-ledger/ledger/verify"),
  createTransfer: (body: { health_id: string; source_repository_id: string; destination_repository_id: string; purpose: string; scope: string }) => request<Transfer>("/migration/transfer-requests", { method: "POST", body: JSON.stringify(body) }),
  transferStatus: (id: string) => request<Transfer>(`/migration/transfers/${id}/status`),
};
