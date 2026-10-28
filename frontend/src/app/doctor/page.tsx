"use client";

import { useEffect, useState } from "react";

import { api, type AuthorizedPatient, type Principal } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function DoctorPortal() {
  const [healthId, setHealthId] = useState("");
  const [purpose, setPurpose] = useState("TREATMENT");
  const [scope, setScope] = useState("clinical");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [authorized, setAuthorized] = useState<AuthorizedPatient[]>([]);
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [resourceType, setResourceType] = useState("Observation");
  const [resourceJson, setResourceJson] = useState("");
  const [saveBusy, setSaveBusy] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    let active = true;
    async function loadInitialData() {
      try {
        const [initialPrincipal, initialPatients] = await Promise.all([
          api.currentPrincipal(),
          api.authorizedPatients(),
        ]);
        if (active) {
          setPrincipal(initialPrincipal);
          setAuthorized(initialPatients);
        }
      } catch (reason: unknown) {
        if (active) setError(reason instanceof Error ? reason.message : "Unable to load doctor workspace");
      }
    }
    void loadInitialData();
    return () => { active = false; };
  }, []);

  async function saveFHIRResource() {
    setSaveMessage("");
    if (!healthId.trim()) {
      setSaveMessage("Select an authorized patient first.");
      return;
    }
    let resource: Record<string, unknown>;
    try {
      resource = JSON.parse(resourceJson) as Record<string, unknown>;
    } catch {
      setSaveMessage("Record JSON is invalid.");
      return;
    }
    setSaveBusy(true);
    try {
      const saved = await api.createFHIRResource(resourceType, {
        ...resource,
        resourceType,
        subject: { reference: `Patient/${healthId}` },
      });
      setSaveMessage(`Record saved successfully${saved.id ? ` (${String(saved.id)})` : ""}.`);
      setResourceJson("");
    } catch (reason: unknown) {
      setSaveMessage(reason instanceof Error ? reason.message : "Unable to save record");
    } finally {
      setSaveBusy(false);
    }
  }

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

      <Card title="Save an authorized FHIR record">
        <div className="grid gap-3 md:grid-cols-3">
          <select value={resourceType} onChange={(e) => setResourceType(e.target.value)} className="rounded-lg border-2 border-slate-400 px-3 py-2 text-sm">
            <option>Observation</option>
            <option>Condition</option>
            <option>MedicationRequest</option>
            <option>Encounter</option>
          </select>
          <p className="md:col-span-2 text-xs text-slate-600">Only consented patients and active repositories are allowed. Patient identity is derived from the selected Health ID.</p>
        </div>
        <textarea
          value={resourceJson}
          onChange={(e) => setResourceJson(e.target.value)}
          placeholder='FHIR fields, for example {"status":"final","code":{"text":"Blood pressure"}}'
          rows={7}
          className="mt-3 w-full rounded-lg border-2 border-slate-400 p-3 font-mono text-xs"
        />
        <button onClick={() => void saveFHIRResource()} disabled={saveBusy || !resourceJson.trim()} className="mt-3 rounded-lg bg-cyan-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
          {saveBusy ? "Validating and saving…" : "Save record"}
        </button>
        {saveMessage && <p className="mt-3 text-sm text-slate-700">{saveMessage}</p>}
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
          <pre className="mt-4 max-h-[520px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </Card>
    </PortalShell>
  );
}
