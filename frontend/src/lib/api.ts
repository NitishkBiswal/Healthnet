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

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function fetchHealth(): Promise<AggregateHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Health API returned HTTP ${response.status}`);
  }

  return response.json() as Promise<AggregateHealthResponse>;
}
