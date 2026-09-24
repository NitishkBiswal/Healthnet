export type ServiceStatus = "healthy" | "degraded" | "unhealthy";

export interface ServiceHealth {
  service: string;
  status: ServiceStatus;
  latency_ms: number | null;
  details?: Record<string, unknown> | null;
}

export interface AggregateHealthResponse {
  status: ServiceStatus;
  version: string;
  services: ServiceHealth[];
}

export interface Patient {
  id: string;
  display_health_id: string;
  issuing_jurisdiction: string;
  given_name: string;
  family_name: string;
  date_of_birth: string;
  sex: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  status: string;
  superseded_by: string | null;
  created_at: string;
}

export interface MatchCandidate {
  patient_id: string;
  health_id: string;
  confidence: number;
  band: string;
}

export interface RegistrationResult {
  outcome: string;
  patient: Patient | null;
  matches: MatchCandidate[];
  duplicate_review_id: string | null;
}

export interface DuplicateReview {
  id: string;
  candidate_patient_id: string;
  confidence: number;
  status: string;
  reviewer_note: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface RegistrationRequest {
  given_name: string;
  family_name: string;
  date_of_birth: string;
  sex?: string;
  phone?: string;
  email?: string;
  address?: string;
  issuing_jurisdiction: string;
  identifiers: {
    identifier_type: string;
    identifier_value: string;
    issuing_authority?: string;
  }[];
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `API returned HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchHealth(): Promise<AggregateHealthResponse> {
  return request<AggregateHealthResponse>("/health");
}

export async function registerPatient(
  payload: RegistrationRequest,
): Promise<RegistrationResult> {
  return request<RegistrationResult>("/identity/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchPatient(healthId: string): Promise<Patient> {
  return request<Patient>(`/identity/${encodeURIComponent(healthId)}`);
}

export async function fetchDuplicateReviews(): Promise<DuplicateReview[]> {
  return request<DuplicateReview[]>("/identity/duplicate-reviews");
}

export async function decideDuplicateReview(
  reviewId: string,
  decision: "APPROVED_DUPLICATE" | "REJECTED",
  reviewerNote?: string,
): Promise<DuplicateReview> {
  return request<DuplicateReview>(`/identity/duplicate-reviews/${reviewId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, reviewer_note: reviewerNote || null }),
  });
}
