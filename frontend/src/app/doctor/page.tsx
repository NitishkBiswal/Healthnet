"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, type AuthorizedPatient, type Principal, type ProviderJurisdictionRequest } from "@/lib/api";

type DoctorTab = "overview" | "patients" | "jurisdiction";

const tabs: { id: DoctorTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "patients", label: "Patients & Records" },
  { id: "jurisdiction", label: "Jurisdiction" },
];
import { Card, PortalShell } from "@/components/portal-shell";

export default function DoctorPortal() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<DoctorTab>("overview");
  const [healthId, setHealthId] = useState("");
  const [purpose, setPurpose] = useState("TREATMENT");
  const [scope, setScope] = useState("clinical");
  const [error, setError] = useState("");
  const [authorized, setAuthorized] = useState<AuthorizedPatient[]>([]);
  const [dismissing, setDismissing] = useState<string | null>(null);
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [jurisdictionRequests, setJurisdictionRequests] = useState<ProviderJurisdictionRequest[]>([]);
  const [requestedJurisdiction, setRequestedJurisdiction] = useState("");
  const [jurisdictionReason, setJurisdictionReason] = useState("");
  const [jurisdictionMessage, setJurisdictionMessage] = useState("");
  const [dismissedConsents, setDismissedConsents] = useState<string[]>([]);
  const [dismissalsLoaded, setDismissalsLoaded] = useState(false);

  // This is a provider-specific dashboard preference. Dismissing a notice
  // never changes the consent record or its audit history.
  useEffect(() => {
    if (!principal?.subject) {
      setDismissedConsents([]);
      setDismissalsLoaded(false);
      return;
    }

    const key = `healthnet:dismissed-consents:${principal.subject}`;
    try {
      const saved = JSON.parse(localStorage.getItem(key) ?? "[]");
      setDismissedConsents(
        Array.isArray(saved)
          ? saved.filter((id): id is string => typeof id === "string")
          : [],
      );
    } catch {
      setDismissedConsents([]);
    } finally {
      setDismissalsLoaded(true);
    }
  }, [principal?.subject]);

  function dismissRepositoryNotice(consentId: string) {
    if (!principal?.subject || !dismissalsLoaded) return;

    const next = [...new Set([...dismissedConsents, consentId])];
    const key = `healthnet:dismissed-consents:${principal.subject}`;
    try {
      localStorage.setItem(key, JSON.stringify(next));
      setDismissedConsents(next);
    } catch {
      setError("Could not save this dashboard preference. Check your browser storage settings.");
    }
  }

  const visibleAuthorized = authorized.filter(
    (patient) =>
      patient.status !== "REVOKED" ||
      !dismissedConsents.includes(patient.consent_id),
  );

  async function loadPrincipal() {
    try {
      const current = await api.currentPrincipal();
      setPrincipal(current);
      if (current.provider_id) {
        setJurisdictionRequests(await api.myJurisdictionRequests());
      }
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load doctor identity");
    }
  }

  async function submitJurisdictionRequest() {
    setError("");
    setJurisdictionMessage("");
    if (jurisdictionReason.trim().length < 10) {
      setError("Please explain the reason for the transfer (at least 10 characters).");
      return;
    }
    try {
      await api.createJurisdictionRequest({
        requested_jurisdiction: requestedJurisdiction.trim().toUpperCase(),
        reason: jurisdictionReason.trim(),
      });
      setJurisdictionMessage("Your jurisdiction transfer request has been submitted for Admin review.");
      setRequestedJurisdiction("");
      setJurisdictionReason("");
      setJurisdictionRequests(await api.myJurisdictionRequests());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not submit jurisdiction transfer request");
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

  async function dismissNotice(consentId: string) {
    setError("");
    setDismissing(consentId);
    try {
      await api.dismissProviderNotice(consentId);
      setAuthorized((items) => items.filter((item) => item.consent_id !== consentId));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to dismiss notice");
    } finally {
      setDismissing(null);
    }
  }

  function openLongitudinalView() {
    setError("");
    if (!healthId) {
      setError("Select an authorized patient first.");
      return;
    }
    router.push(
      `/doctor/longitudinal?health_id=${encodeURIComponent(healthId)}&purpose=${encodeURIComponent(purpose)}&scope=${encodeURIComponent(scope)}`,
    );
  }

  return (
    <PortalShell
      requiredRole="provider"
      title="Doctor Portal"
      description="Review patients who have granted you access and open their clinical history when needed."
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-sm">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              aria-current={activeTab === tab.id ? "page" : undefined}
              className={`rounded-lg px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-slate-950 text-white shadow" : "text-slate-700 hover:bg-slate-100"}`}
            >
              {tab.label}
              {tab.id === "patients" && authorized.length > 0 && (
                <span className={`ml-2 rounded-full px-2 py-0.5 text-xs ${activeTab === tab.id ? "bg-white/20 text-white" : "bg-cyan-100 text-cyan-900"}`}>{authorized.length}</span>
              )}
              {tab.id === "jurisdiction" && jurisdictionRequests.some((item) => item.status === "PENDING") && (
                <span className={`ml-2 inline-block h-2 w-2 rounded-full ${activeTab === tab.id ? "bg-amber-300" : "bg-amber-500"}`} aria-label="Pending request" />
              )}
            </button>
          ))}
          <button
            type="button"
            onClick={() => { void loadPrincipal(); void loadAuthorized(); }}
            className="ml-auto rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            Refresh data
          </button>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">HealthNet Provider ID</p>
                <p className="mt-2 font-mono text-lg font-bold text-slate-950">{principal?.provider_id || "Not linked"}</p>
                <p className="mt-1 text-xs text-slate-500">Share this ID with patients when they grant consent.</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">Patients with access</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-slate-950">{visibleAuthorized.filter((patient) => patient.status !== "REVOKED").length}</p>
                <p className="mt-1 text-xs text-slate-500">Patients with current consent or authorization.</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">Registered jurisdiction</p>
                <p className="mt-2 font-mono text-lg font-bold text-slate-950">{principal?.provider_jurisdiction || "Not available"}</p>
                <p className="mt-1 text-xs text-slate-500">{jurisdictionRequests.filter((item) => item.status === "PENDING").length} pending transfer requests.</p>
              </div>
            </div>
            <Card title="Workspace shortcuts">
              <p className="mb-4 text-sm text-slate-600">Choose a workspace area to continue.</p>
              <div className="grid gap-3 md:grid-cols-2">
                <button type="button" onClick={() => setActiveTab("patients")} className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-cyan-500 hover:bg-cyan-50">
                  <p className="font-bold text-slate-950">Patients & Records</p>
                  <p className="mt-1 text-sm text-slate-600">Review patient consent and open authorized longitudinal records.</p>
                </button>
                <button type="button" onClick={() => setActiveTab("jurisdiction")} className="rounded-xl border border-slate-200 p-4 text-left transition hover:border-cyan-500 hover:bg-cyan-50">
                  <p className="font-bold text-slate-950">Jurisdiction</p>
                  <p className="mt-1 text-sm text-slate-600">View your registered region and request an Admin-approved transfer.</p>
                </button>
              </div>
            </Card>
          </div>
        )}

        {activeTab === "patients" && (
          <div className="space-y-5">
            <Card title="Your HealthNet Provider ID">
          <p className="text-sm text-slate-700">
            Patients use this Provider ID when granting you consent.
          </p>
          <p className="mt-2 rounded-lg bg-cyan-50 px-3 py-2 font-mono text-sm font-bold text-slate-950">
            {principal?.provider_id || "Not linked to a HealthNet provider"}
          </p>
          {!principal?.provider_id && principal?.subject && (
            <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950">
              <p className="font-semibold">This account is not linked to a HealthNet Provider record yet.</p>
              <p className="mt-1 break-all font-mono">{principal.subject}</p>
            </div>
          )}
        </Card>

          </div>
        )}

        {activeTab === "jurisdiction" && (
          <div className="space-y-5">
        <Card title="Your jurisdiction">
          <p className="text-sm text-slate-700">Your current registered jurisdiction</p>
          <p className="mt-2 rounded-lg bg-cyan-50 px-3 py-2 font-mono text-sm font-bold text-slate-950">{principal?.provider_jurisdiction || "Not available"}</p>
          <p className="mt-3 text-xs text-slate-600">If you move to a hospital in another jurisdiction, submit a request here. Only an Admin can approve the change; your registered jurisdiction remains unchanged until approval.</p>
          {jurisdictionRequests.some((item) => item.status === "PENDING") ? (
            <p className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm font-semibold text-amber-900">You already have a pending jurisdiction transfer request. Wait for Admin review before submitting another.</p>
          ) : (
            <div className="mt-3 space-y-3">
              <input value={requestedJurisdiction} onChange={(event) => setRequestedJurisdiction(event.target.value)} placeholder="Requested jurisdiction (e.g. IN-KA)" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900" />
              <textarea value={jurisdictionReason} onChange={(event) => setJurisdictionReason(event.target.value)} rows={2} maxLength={1000} placeholder="Explain why you need to transfer to this jurisdiction (minimum 10 characters)." className="w-full rounded-lg border border-slate-300 p-3 text-sm text-slate-900" />
              <button type="button" onClick={() => void submitJurisdictionRequest()} disabled={requestedJurisdiction.trim().length < 2 || jurisdictionReason.trim().length < 10} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white disabled:opacity-40">Submit jurisdiction transfer request</button>
              {jurisdictionMessage && <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">{jurisdictionMessage}</p>}
            </div>
          )}
          {jurisdictionRequests.length > 0 && <div className="mt-4 space-y-2">
            <p className="text-sm font-bold text-slate-800">Request history</p>
            {jurisdictionRequests.map((item) => <div key={item.id} className="rounded-lg border border-slate-200 p-3 text-sm">
              <div className="flex flex-wrap justify-between gap-2"><strong>{item.current_jurisdiction} → {item.requested_jurisdiction}</strong><span className="font-bold">{item.status}</span></div>
              <p className="mt-1 text-slate-600">Reason: {item.reason}</p>
              <p className="mt-1 text-xs text-slate-500">Submitted {new Date(item.created_at).toLocaleString()}</p>
              {item.reviewer_note && <p className="mt-2 rounded-lg bg-red-50 p-2 text-sm text-red-900">Admin response: {item.reviewer_note}</p>}
            </div>)}
          </div>}
        </Card>

        <Card title="Patients who have granted you access">
          {visibleAuthorized.length === 0 ? (
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-700">
                No patients have currently granted you access.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {visibleAuthorized.map((patient) => {
                const selected = healthId === patient.health_id;
                const needsRenewal = patient.status === "REVOKED";
                if (needsRenewal) {
                  return (
                    <div
                      key={patient.consent_id}
                      className="rounded-xl border-2 border-amber-300 bg-amber-50 p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-base font-bold text-slate-950">
                          {patient.given_name} {patient.family_name}
                        </span>
                        <span className="rounded-full bg-white px-3 py-1 font-mono text-xs font-bold text-slate-700">
                          {patient.health_id}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                        <p className="text-sm font-bold text-amber-900">
                          Patient repository changed
                        </p>
                        <button
                          type="button"
                          onClick={() => dismissRepositoryNotice(patient.consent_id)}
                          disabled={!dismissalsLoaded}
                          aria-label={`Remove outdated notice for ${patient.given_name} ${patient.family_name}`}
                          className="rounded-lg border border-amber-400 bg-white px-3 py-1.5 text-xs font-bold text-amber-950 hover:bg-amber-100 disabled:opacity-50"
                        >
                          Remove from list
                        </button>
                      </div>
                      <p className="mt-1 text-sm text-amber-900">
                        This patient's records have moved to a different healthcare repository. Your previous consent was revoked for the transfer. Ask the patient to grant consent again before opening their updated medical records.
                      </p>
                      <button
                        type="button"
                        onClick={() => void dismissNotice(patient.consent_id)}
                        disabled={dismissing === patient.consent_id}
                        className="mt-3 rounded-lg border border-amber-500 bg-white px-3 py-2 text-sm font-semibold text-amber-950 hover:bg-amber-100 disabled:opacity-50"
                      >
                        {dismissing === patient.consent_id ? "Dismissing..." : "Dismiss notice"}
                      </button>
                    </div>
                  );
                }
                return (
                  <button
                    key={patient.consent_id}
                    onClick={() => {
                      setHealthId(patient.health_id);
                      setPurpose(patient.purpose);
                      setScope(patient.scopes[0] ?? "clinical");
                      setError("");
                    }}
                    className={`block w-full rounded-xl border-2 p-4 text-left transition ${
                      selected
                        ? "border-cyan-600 bg-cyan-50"
                        : "border-slate-200 bg-white hover:border-slate-400 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-base font-bold text-slate-950">
                        {patient.given_name} {patient.family_name}
                      </span>
                      <span className="rounded-full bg-white px-3 py-1 font-mono text-xs font-bold text-slate-700">
                        {patient.health_id}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-600">
                      Access purpose: <span className="font-semibold">{patient.purpose}</span>
                      {" · "}
                      Permission: <span className="font-semibold">{patient.scopes.join(", ")}</span>
                    </p>
                    <p className="mt-2 text-xs font-semibold text-cyan-800">
                      {selected ? "Patient selected" : "Select patient to view record"}
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

          </div>
        )}

        {activeTab === "patients" && (
          <div className="space-y-5">
        <Card title="Patient record">
          {healthId ? (
            <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-5">
              <p className="text-xs font-bold uppercase tracking-wide text-cyan-800">Selected patient</p>
              <h2 className="mt-1 text-xl font-bold text-slate-950">
                {authorized.find((patient) => patient.health_id === healthId)?.given_name}{" "}
                {authorized.find((patient) => patient.health_id === healthId)?.family_name}
              </h2>
              <p className="mt-1 font-mono text-sm text-slate-700">{healthId}</p>
              <p className="mt-3 text-sm text-slate-700">
                Open the dedicated clinical view to review the patient's demographics, current record repository, and clinical history.
              </p>
              <button
                onClick={openLongitudinalView}
                className="mt-4 rounded-lg bg-slate-950 px-5 py-2.5 text-sm font-bold text-white hover:bg-slate-800"
              >
                Open Longitudinal Record →
              </button>
            </div>
          ) : (
            <div className="rounded-lg bg-slate-50 p-5">
              <p className="text-sm font-semibold text-slate-700">
                Select a patient above to open their authorized clinical record.
              </p>
              <p className="mt-1 text-xs text-slate-500">
                The detailed record opens on a separate page so the doctor dashboard stays uncluttered.
              </p>
            </div>
          )}
          {error && <p className="mt-3 text-sm font-semibold text-red-600">{error}</p>}
        </Card>
          </div>
        )}
        {error && (
          <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>
        )}
      </div>
    </PortalShell>
  );
}
