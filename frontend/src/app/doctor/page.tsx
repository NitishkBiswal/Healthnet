"use client";

import { useEffect, useState } from "react";

import {
  api,
  type AuthorizedPatient,
  type BreakGlassGrant,
  type Principal,
  type ProvenanceResource,
} from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function DoctorPortal() {
  const [healthId, setHealthId] = useState("");
  const [purpose, setPurpose] = useState("TREATMENT");
  const [scope, setScope] = useState("clinical");
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.longitudinal>> | null>(null);
  const [error, setError] = useState("");
  const [authorized, setAuthorized] = useState<AuthorizedPatient[]>([]);
  const [authorizedOffset, setAuthorizedOffset] = useState(0);
  const [hasMoreAuthorized, setHasMoreAuthorized] = useState(false);
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [resourceType, setResourceType] = useState("Observation");
  const [resourceJson, setResourceJson] = useState("");
  const [saveBusy, setSaveBusy] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [loadingView, setLoadingView] = useState(false);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [resourceTypes, setResourceTypes] = useState<string[]>([]);
  const [breakGlassReason, setBreakGlassReason] = useState("");
  const [breakGlass, setBreakGlass] = useState<BreakGlassGrant | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [provenance, setProvenance] = useState<ProvenanceResource[]>([]);

  useEffect(() => {
    if (!breakGlass) return;
    const updateTime = () => setCurrentTime(Date.now());
    updateTime();
    const timer = window.setInterval(updateTime, 1000);
    return () => window.clearInterval(timer);
  }, [breakGlass]);

  useEffect(() => {
    let active = true;
    async function loadInitialData() {
      try {
        const [initialPrincipal, initialPatients] = await Promise.all([
          api.currentPrincipal(),
          api.authorizedPatients(0, 50),
        ]);
        if (active) {
          setPrincipal(initialPrincipal);
          setAuthorized(initialPatients);
          setHasMoreAuthorized(initialPatients.length === 50);
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
      setLoadingView(true);
      const activeGrant = breakGlass
        && breakGlass.health_id === healthId
        && Date.parse(breakGlass.expires_at) > Date.now()
        ? breakGlass
        : null;
      setResult(await api.longitudinal(healthId, purpose, scope, {
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        resource_types: resourceTypes,
        breakGlassToken: activeGrant?.authorization_token,
      }));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Authorization or retrieval failed");
    } finally {
      setLoadingView(false);
    }
  }

  async function invokeBreakGlass() {
    setError("");
    if (!healthId.trim() || breakGlassReason.trim().length < 5) {
      setError("Select an authorized patient and provide an emergency reason.");
      return;
    }
    try {
      const grant = await api.breakGlass(healthId.trim(), breakGlassReason.trim());
      setBreakGlass(grant);
      setPurpose("EMERGENCY");
      setScope("clinical");
      setBreakGlassReason("");
      setError("");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to invoke emergency access");
    }
  }

  async function loadMoreAuthorized() {
    const nextOffset = authorizedOffset + 50;
    try {
      const next = await api.authorizedPatients(nextOffset, 50);
      setAuthorized((current) => [...current, ...next]);
      setAuthorizedOffset(nextOffset);
      setHasMoreAuthorized(next.length === 50);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load more patients");
    }
  }

  async function loadProvenance() {
    setError("");
    try {
      setProvenance(await api.provenance(healthId));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load record history");
    }
  }

  function toggleResourceType(resourceType: string) {
    setResourceTypes((current) => current.includes(resourceType)
      ? current.filter((value) => value !== resourceType)
      : [...current, resourceType]);
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
                  setBreakGlass(null);
                  setProvenance([]);
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
        {hasMoreAuthorized && (
          <button onClick={() => void loadMoreAuthorized()} className="mt-3 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">
            Load more patients
          </button>
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
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-700">From date
            <Field type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
          </label>
          <label className="text-sm font-medium text-slate-700">To date
            <Field type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
          </label>
        </div>
        <fieldset className="mt-3">
          <legend className="text-sm font-semibold">FHIR resource types (optional)</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {["Observation", "Condition", "MedicationRequest", "Encounter", "Procedure", "DiagnosticReport", "Immunization", "AllergyIntolerance"].map((type) => (
              <label key={type} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={resourceTypes.includes(type)} onChange={() => toggleResourceType(type)} />
                {type}
              </label>
            ))}
          </div>
        </fieldset>
        <button
          onClick={() => void load()}
          disabled={!healthId}
          className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loadingView ? "Loading records…" : "Request longitudinal view"}
        </button>
        <div className="mt-5 rounded-xl border border-amber-300 bg-amber-50 p-4">
          <h3 className="font-semibold text-amber-950">Emergency break-glass access</h3>
          <p className="mt-1 text-sm text-amber-900">
            Grants this provider temporary, audited access to this patient&apos;s clinical records for 15 minutes. The patient is notified.
          </p>
          <Field
            value={breakGlassReason}
            onChange={(event) => setBreakGlassReason(event.target.value)}
            placeholder="Document the emergency reason"
            className="mt-3"
          />
          <button onClick={() => void invokeBreakGlass()} disabled={!healthId || breakGlassReason.trim().length < 5} className="mt-3 rounded-lg bg-amber-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
            Invoke break-glass
          </button>
          {breakGlass && Date.parse(breakGlass.expires_at) > currentTime && breakGlass.health_id === healthId && (
            <p className="mt-2 text-sm font-semibold text-amber-950">
              Emergency access active until {new Date(breakGlass.expires_at).toLocaleTimeString()}. Request an EMERGENCY-purpose longitudinal view to use it.
            </p>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        {result !== null && <div className="mt-4 space-y-3">
          <p className="text-sm font-semibold">Status: {result.completeness} · {result.repositories_available}/{result.repositories_checked} repositories</p>
          {result.records.map((record, index) => {
            const resource = record.resource;
            const title = (resource.code as { text?: string } | undefined)?.text
              || (resource.medicationCodeableConcept as { text?: string } | undefined)?.text
              || `${record.resource_type} record`;
            const date = String(resource.effectiveDateTime || resource.issued || resource.recorded || resource.date || "");
            return <details key={`${record.repository}-${record.resource_type}-${String(resource.id ?? index)}`} className="rounded-lg border border-slate-300 p-4">
              <summary className="cursor-pointer font-semibold">{title} · {record.resource_type} · {record.repository}{date ? ` · ${date}` : ""}</summary>
              <pre className="mt-3 max-h-80 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(resource, null, 2)}</pre>
            </details>;
          })}
          {result.errors.map((message, index) => <p key={`${index}-${message}`} className="text-sm text-amber-800">{message}</p>)}
        </div>}
        <div className="mt-5">
          <button onClick={() => void loadProvenance()} disabled={!healthId} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">Load record history</button>
          {provenance.length > 0 && <ol className="mt-3 space-y-2 border-l-2 border-cyan-300 pl-4">
            {provenance.map((entry) => <li key={entry.id} className="text-sm">
              <span className="font-semibold">{entry.activity.coding?.[0]?.display ?? "Record change"}</span>
              <span className="ml-2 text-slate-600">{entry.target[0]?.reference} · {new Date(entry.recorded).toLocaleString()}</span>
            </li>)}
          </ol>}
        </div>
      </Card>
    </PortalShell>
  );
}
