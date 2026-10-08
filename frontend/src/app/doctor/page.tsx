"use client";

import { useEffect, useState } from "react";

import { api, type AuthorizedPatient } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function DoctorPortal() {
  const [healthId, setHealthId] = useState("");
  const [purpose, setPurpose] = useState("TREATMENT");
  const [scope, setScope] = useState("clinical");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [authorized, setAuthorized] = useState<AuthorizedPatient[]>([]);
  const [principal, setPrincipal] = useState("");

  async function loadAuthorized() {
    try {
      const [patients, me] = await Promise.all([
        api.authorizedPatients(),
        api.currentPrincipal(),
      ]);
      setAuthorized(patients);
      setPrincipal(me.subject);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load authorized patients");
    }
  }

  useEffect(() => {
    void loadAuthorized();
  }, []);

  async function load() {
    setError("");
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
      <Card title="Your HealthNet identifier">
        <p className="text-sm text-slate-700">
          Patients use this identifier when granting you consent.
        </p>
        <p className="mt-2 rounded-lg bg-cyan-50 px-3 py-2 font-mono text-sm text-slate-950">
          {principal || "Loading..."}
        </p>
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
          <Field
            value={healthId}
            onChange={(e) => setHealthId(e.target.value)}
            placeholder="Health ID"
          />
          <Field
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            placeholder="Purpose"
          />
          <Field
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            placeholder="Scope"
          />
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
          <pre className="mt-4 max-h-[520px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </Card>
    </PortalShell>
  );
}
