"use client";

import { useEffect, useState } from "react";

import { api, type AuthorizedPatient, type Principal } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

function formatResource(resource: any) {
  const codeText =
    resource?.code?.text ||
    resource?.code?.coding?.[0]?.display ||
    resource?.medicationCodeableConcept?.text ||
    resource?.medicationCodeableConcept?.coding?.[0]?.display ||
    resource?.resourceType ||
    "FHIR Resource";

  if (resource?.resourceType === "Observation") {
    if (resource.valueQuantity) {
      return `${codeText}: ${resource.valueQuantity.value} ${resource.valueQuantity.unit || ""}`.trim();
    }
    if (resource.component) {
      return resource.component
        .map((item: any) => `${item.code?.text || item.code?.coding?.[0]?.display || "Value"}: ${item.valueQuantity?.value} ${item.valueQuantity?.unit || ""}`.trim())
        .join(" · ");
    }
    if (resource.valueString) return `${codeText}: ${resource.valueString}`;
  }

  if (resource?.resourceType === "Condition") {
    return codeText;
  }

  if (resource?.resourceType === "MedicationRequest") {
    return `${codeText}${resource.dosageInstruction?.[0]?.text ? ` — ${resource.dosageInstruction[0].text}` : ""}`;
  }

  if (resource?.resourceType === "Encounter") {
    return resource.serviceProvider?.display || resource.class?.display || "Clinical encounter";
  }

  return codeText;
}

function resourceDate(resource: any) {
  return (
    resource?.effectiveDateTime ||
    resource?.onsetDateTime ||
    resource?.authoredOn ||
    resource?.period?.start ||
    resource?.recordedDate ||
    ""
  );
}

export default function DoctorPortal() {
  const [healthId, setHealthId] = useState("");
  const [purpose, setPurpose] = useState("TREATMENT");
  const [scope, setScope] = useState("clinical");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [authorized, setAuthorized] = useState<AuthorizedPatient[]>([]);
  const [principal, setPrincipal] = useState<Principal | null>(null);\n  const [showRaw, setShowRaw] = useState(false);

  async function loadPrincipal() {
    try {
      setPrincipal(await api.currentPrincipal());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load doctor identity");
    }
  }

  async function loadAuthorized() {
    try {
      setAuthorized(await api.authorizedPatients());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load authorized patients");
    }
  }

  useEffect(() => {
    void loadPrincipal();
    void loadAuthorized();
  }, []);

  async function load() {
    setError("");
    if (!healthId) {
      setError("Select an authorized patient first.");
      return;
    }
    try {
      setResult(await api.longitudinal(healthId, purpose, scope));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Authorization or retrieval failed");
    }
  }

  return (
    <PortalShell
      requiredRole="provider"
      title="Doctor Portal"
      description="Federated longitudinal access is subject to authentication, consent and jurisdiction policy."
    >
      <Card title="Your HealthNet Provider ID">
        <p className="text-sm text-slate-700">
          Patients use this Provider ID when granting you consent.
        </p>
        <p className="mt-2 rounded-lg bg-cyan-50 px-3 py-2 font-mono text-sm text-slate-950">
          {principal?.provider_id || "Not linked to a HealthNet provider"}
        </p>
        {!principal?.provider_id && principal?.subject && (
          <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950">
            <p className="font-semibold">
              This Keycloak account is not linked to a HealthNet Provider record yet.
            </p>
            <p className="mt-1">
              An administrator can use the following account subject to create the provider mapping:
            </p>
            <p className="mt-1 break-all font-mono">{principal.subject}</p>
          </div>
        )}
      </Card>

      <Card title="Patients who have granted you consent">
        {authorized.length === 0 ? (
          <p className="text-sm text-slate-600">
            No active patient consents are currently linked to your account.
          </p>
        ) : (
          <div className="space-y-3">
            {authorized.map((patient) => (
              <button
                key={patient.consent_id}
                onClick={() => {
                  setHealthId(patient.health_id);
                  setPurpose(patient.purpose);
                  setScope(patient.scopes[0] ?? "clinical");
                  setResult(null);
                  setError("");
                }}
                className="block w-full rounded-xl border border-slate-300 p-4 text-left hover:bg-slate-50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-bold text-slate-950">
                    {patient.given_name} {patient.family_name}
                  </span>
                  <span className="font-mono text-sm text-slate-700">
                    {patient.health_id}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-600">
                  Purpose: {patient.purpose} · Scope: {patient.scopes.join(", ")}
                  {patient.valid_until
                    ? ` · Until ${new Date(patient.valid_until).toLocaleDateString()}`
                    : " · No expiry"}
                </p>
              </button>
            ))}
          </div>
        )}
      </Card>

      <Card title="Authorized patient record view">
        <div className="grid gap-3 md:grid-cols-3">
          <Field value={healthId} onChange={(e) => setHealthId(e.target.value)} placeholder="Health ID" />
          <Field value={purpose} onChange={(e) => setPurpose(e.target.value)} placeholder="Purpose" />
          <Field value={scope} onChange={(e) => setScope(e.target.value)} placeholder="Scope" />
        </div>
        <button
          onClick={load}
          disabled={!healthId}
          className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Request longitudinal view
        </button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {result !== null && (
          <div className="mt-5">
            {(() => {
              const view = result as {
                health_id: string;
                completeness: string;
                repositories_checked: number;
                repositories_available: number;
                errors: string[];
                records: Array<{ repository: string; resource_type: string; resource: any }>;
              };
              const records = [...view.records].sort((a, b) =>
                resourceDate(a.resource).localeCompare(resourceDate(b.resource))
              );
              const grouped = records.reduce<Record<string, typeof records>>((groups, record) => {
                (groups[record.repository] ||= []).push(record);
                return groups;
              }, {});

              return (
                <>
                  <div className="grid gap-3 sm:grid-cols-4">
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">Health ID</p>
                      <p className="mt-1 font-mono font-bold text-slate-950">{view.health_id}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">Repositories</p>
                      <p className="mt-1 font-bold text-slate-950">{view.repositories_available} / {view.repositories_checked}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">Completeness</p>
                      <p className="mt-1 font-bold text-slate-950">{view.completeness}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">FHIR records</p>
                      <p className="mt-1 font-bold text-slate-950">{view.records.length}</p>
                    </div>
                  </div>

                  {view.errors.length > 0 && (
                    <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
                      <p className="font-semibold">Repository warnings</p>
                      {view.errors.map((item, index) => <p key={index} className="mt-1">{item}</p>)}
                    </div>
                  )}

                  <div className="mt-5 space-y-4">
                    {Object.entries(grouped).map(([repository, repositoryRecords]) => (
                      <div key={repository} className="rounded-xl border border-slate-200 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <h3 className="font-bold text-slate-950">{repository}</h3>
                          <span className="rounded-full bg-cyan-50 px-2 py-1 text-xs font-semibold text-cyan-900">
                            {repositoryRecords.length} FHIR record{repositoryRecords.length === 1 ? "" : "s"}
                          </span>
                        </div>
                        <div className="mt-3 space-y-3">
                          {repositoryRecords.map((record) => (
                            <div key={`${record.repository}-${record.resource_type}-${record.resource.id}`} className="rounded-lg bg-slate-50 p-3">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="font-semibold text-slate-950">{record.resource_type}</span>
                                {resourceDate(record.resource) && (
                                  <span className="text-xs text-slate-500">
                                    {new Date(resourceDate(record.resource)).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                              <p className="mt-1 text-sm text-slate-700">{formatResource(record.resource)}</p>
                              <p className="mt-1 font-mono text-[11px] text-slate-400">FHIR ID: {record.resource.id}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => setShowRaw((value) => !value)}
                    className="mt-5 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    {showRaw ? "Hide raw FHIR response" : "Inspect raw FHIR response"}
                  </button>
                  {showRaw && (
                    <pre className="mt-3 max-h-[520px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  )}
                </>
              );
            })()}
          </div>
        )}
      </Card>
    </PortalShell>
  );
}
