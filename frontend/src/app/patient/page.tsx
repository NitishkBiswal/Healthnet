"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type Consent, type DuplicateReview, type Patient } from "@/lib/api";
import { Card, PortalShell } from "@/components/portal-shell";

export default function PatientPortal() {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [reviews, setReviews] = useState<DuplicateReview[]>([]);
  const [consents, setConsents] = useState<Consent[]>([]);
  const [emergency, setEmergency] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [purpose, setPurpose] = useState("TREATMENT");
  const [scope, setScope] = useState("clinical");
  const [validUntil, setValidUntil] = useState("");
  const [consentMessage, setConsentMessage] = useState("");
  const [consentBusy, setConsentBusy] = useState(false);

  useEffect(() => {
    void api.myPatient()
      .then((value) => {
        setPatient(value);
        void api.consents(value.display_health_id).then(setConsents).catch(() => {});
      })
      .catch(() => {});
    void api.myDuplicateReviews().then(setReviews).catch(() => {});
  }, []);

  async function run<T>(fn: () => Promise<T>, setter: (value: T) => void) {
    setError("");
    try {
      setter(await fn());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Request failed");
    }
  }

  async function revokeConsent(consent: Consent) {
    if (!window.confirm(`Revoke access for ${consent.grantee_id}? This takes effect immediately.`)) return;
    setConsentBusy(true);
    setConsentMessage("");
    try {
      await api.revokeConsent(consent.id);
      setConsents((current) => current.map((item) => item.id === consent.id
        ? { ...item, status: "REVOKED", revoked_at: new Date().toISOString() }
        : item));
      setConsentMessage("Permission revoked successfully. The provider can no longer access this patient record.");
    } catch (reason: unknown) {
      setConsentMessage(reason instanceof Error ? reason.message : "Unable to revoke permission");
    } finally {
      setConsentBusy(false);
    }
  }

  async function grantConsent() {
    if (!patient || !doctorId.trim()) {
      setConsentMessage("Enter the doctor's HealthNet Provider ID.");
      return;
    }
    setConsentMessage("");
    try {
      await api.createConsent({
        health_id: patient.display_health_id,
        grantee_type: "PROVIDER",
        grantee_id: doctorId.trim(),
        purpose,
        scopes: [scope],
        valid_from: new Date().toISOString(),
        ...(validUntil ? { valid_until: new Date(validUntil).toISOString() } : {}),
      });
      setConsentMessage("Consent granted successfully.");
      setDoctorId("");
      setValidUntil("");
      setConsents(await api.consents(patient.display_health_id));
    } catch (reason: unknown) {
      setConsentMessage(reason instanceof Error ? reason.message : "Unable to grant consent");
    }
  }

  return (
    <PortalShell
      requiredRole="patient"
      title="Patient Portal"
      description="Your Health ID, permissions and emergency profile."
    >
      {!patient && (
        <div className="mb-5 flex flex-wrap gap-3">
          <Link href="/patient/onboarding" className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-bold text-slate-950 hover:bg-cyan-400">
            Get my Health ID
          </Link>
        </div>
      )}

      {reviews.length > 0 && (
        <Card title="Identity review status">
          <div className="space-y-2">
            {reviews.map((review) => (
              <div key={review.id} className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
                <p className="font-semibold">Duplicate review: {review.status}</p>
                <p className="mt-1">Confidence {review.confidence.toFixed(2)} · submitted {new Date(review.created_at).toLocaleString()}</p>
                <p className="mt-1">The Auditor Portal is reviewing this identity match.</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="My Health ID">
          {patient ? (
            <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-5">
              <p className="text-sm text-slate-600">Your permanent Health ID</p>
              <p className="mt-1 text-3xl font-bold tracking-wide text-slate-950">{patient.display_health_id}</p>
              <p className="mt-2 text-sm text-slate-700">{patient.given_name} {patient.family_name} · {patient.issuing_jurisdiction}</p>
            </div>
          ) : (
            <p className="text-sm text-slate-600">You have not registered a Health ID yet. Use <strong>Get my Health ID</strong> above.</p>
          )}
        </Card>

        <Card title="Consent & emergency profile">
          {patient && (
            <div className="mb-5 rounded-xl border border-cyan-200 bg-cyan-50 p-4">
              <h3 className="font-bold text-slate-950">Grant a doctor access</h3>
              <p className="mt-1 text-sm text-slate-700">
                Enter the doctor&apos;s HealthNet Provider ID from their Doctor Workspace.
              </p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <input value={doctorId} onChange={(e) => setDoctorId(e.target.value)} placeholder="Doctor Provider ID (e.g. PRV-IN-000001)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <select value={purpose} onChange={(e) => setPurpose(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="TREATMENT">Treatment</option>
                  <option value="EMERGENCY">Emergency</option>
                  <option value="RESEARCH">Research</option>
                </select>
                <select value={scope} onChange={(e) => setScope(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="clinical">Clinical records</option>
                  <option value="medications">Medications</option>
                  <option value="laboratory">Laboratory results</option>
                  <option value="full">Full record</option>
                </select>
                <input type="datetime-local" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <button onClick={grantConsent} className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800">Grant consent</button>
              {consentMessage && <p className="mt-2 text-sm text-slate-700">{consentMessage}</p>}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <button onClick={() => run(() => api.consents(patient?.display_health_id || ""), setConsents)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-50">
              View consent
            </button>
            <button onClick={() => run(() => api.emergency(patient?.display_health_id || ""), setEmergency)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-50">
              Emergency profile
            </button>
          </div>
          {consents.length > 0 && (
            <div className="mt-4 space-y-2">
              {consents.map((consent) => (
                <div key={consent.id} className="rounded-lg border border-slate-300 p-3 text-sm">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-950">{consent.grantee_id}</p>
                      <p className="text-xs text-slate-600">{consent.purpose} · {consent.scopes.join(", ")} · {consent.status}</p>
                    </div>
                    {consent.status === "ACTIVE" && (
                      <button
                        disabled={consentBusy}
                        onClick={() => void revokeConsent(consent)}
                        className="rounded-lg border border-red-300 px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-50 disabled:opacity-60"
                      >
                        Revoke permission
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
          {emergency !== null && <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(emergency, null, 2)}</pre>}
          {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        </Card>
      </div>
    </PortalShell>
  );
}
