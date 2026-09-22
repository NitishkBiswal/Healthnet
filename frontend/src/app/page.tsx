"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchHealth, type ServiceHealth } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    healthy: "bg-green-100 text-green-800",
    degraded: "bg-yellow-100 text-yellow-800",
    unhealthy: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] || "bg-gray-100 text-gray-800"}`}
    >
      {status}
    </span>
  );
}

function ServiceCard({ service }: { service: ServiceHealth }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-900">{service.service}</h3>
        <StatusBadge status={service.status} />
      </div>
      <p className="text-xs text-gray-500">
        {service.latency_ms !== null ? `${service.latency_ms}ms` : "N/A"}
      </p>
    </div>
  );
}

export default function Home() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 15000,
  });

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-4xl px-4 py-16">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold tracking-tight text-gray-900">
            HealthNet
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-gray-600">
            Global Federated Health Identity &amp; Interoperability Network
          </p>
          <p className="mt-2 text-sm italic text-gray-500">
            &ldquo;The patient carries the identity, not the medical
            database.&rdquo;
          </p>
        </div>

        {/* System Status */}
        <div className="mb-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                System Status
              </h2>
              <p className="text-sm text-gray-500">
                Infrastructure health dashboard
              </p>
            </div>
            {data && <StatusBadge status={data.status} />}
            {isLoading && (
              <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-800">
                Checking...
              </span>
            )}
            {isError && <StatusBadge status="unhealthy" />}
          </div>

          {isLoading && (
            <p className="text-sm text-gray-500">Connecting to backend...</p>
          )}
          {isError && (
            <p className="text-sm text-red-600">
              Cannot reach backend API:{" "}
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          )}
          {data && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {data.services.map((service) => (
                <ServiceCard key={service.service} service={service} />
              ))}
            </div>
          )}
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-3 text-base font-semibold text-gray-900">
              Architecture
            </h3>
            <ul className="space-y-1 text-sm text-gray-600">
              <li>• Federated identity — one permanent Health ID per patient</li>
              <li>• Distributed records — data stays at point of care</li>
              <li>• Consent-gated retrieval — never unrestricted access</li>
              <li>• Jurisdiction-aware policy — law-agnostic engine</li>
              <li>• FHIR R4 interoperability</li>
            </ul>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-3 text-base font-semibold text-gray-900">
              Technology
            </h3>
            <ul className="space-y-1 text-sm text-gray-600">
              <li>• Backend: Python / FastAPI</li>
              <li>• Frontend: Next.js / TypeScript</li>
              <li>• FHIR Server: HAPI FHIR R4</li>
              <li>• Auth: Keycloak (OAuth2/OIDC)</li>
              <li>• Database: PostgreSQL + Redis</li>
            </ul>
          </div>
        </div>

        {/* Version footer */}
        <p className="mt-12 text-center text-xs text-gray-400">
          HealthNet v0.1.0 — Segment 0 (Foundation)
        </p>
      </div>
    </main>
  );
}
