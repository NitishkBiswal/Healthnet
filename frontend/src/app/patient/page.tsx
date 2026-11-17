"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type AadhaarStatus, type Consent, type CurrentRecordLocation, type DuplicateReview, type Patient, type Transfer } from "@/lib/api";
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
  const [currentLocation, setCurrentLocation] = useState<CurrentRecordLocation | null>(null);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [migrationMessage, setMigrationMessage] = useState("");
  const [aadhaarStatus, setAadhaarStatus] = useState<AadhaarStatus | null>(null);
  const [aadhaarNumber, setAadhaarNumber] = useState("");
  const [aadhaarMessage, setAadhaarMessage] = useState("");

  useEffect(() => {
    void api.myPatient().then(async (value) => {
      setPatient(value);
      try { setAadhaarStatus(await api.myAadhaarStatus()); } catch {}
      try { setConsents(await api.consents(value.display_health_id)); } catch {}
      try { setCurrentLocation(await api.currentRecordLocation(value.display_health_id)); } catch {}
      try { setTransfers(await api.myTransfers()); } catch {}
    }).catch(() => {});
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

  async function saveAadhaar() {
    setAadhaarMessage("");
    try {
      const status = await api.updateMyAadhaar(aadhaarNumber);
      setAadhaarStatus(status);
      setAadhaarNumber("");
      setAadhaarMessage("Aadhaar saved securely. HealthNet has not verified it with UIDAI.");
    } catch (reason: unknown) {
      setAadhaarMessage(reason instanceof Error ? reason.message : "Unable to save Aadhaar");
    }
  }

  async function revokeConsent(consentId: string) {
    if (!patient) return;
    setConsentMessage("");
    try {
      const updated = await api.revokeConsent(consentId);
      setConsents((items) => items.map((item) => item.id === updated.id ? updated : item));
      setConsentMessage("Consent revoked. This provider can no longer use this consent for new access.");
    } catch (reason: unknown) {
      setConsentMessage(reason instanceof Error ? reason.message : "Unable to revoke consent");
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

      {transfers.some((transfer) => transfer.state === "REQUESTED") && (
        <Card title="Patient authorization required">
          <div className="space-y-3">
            {transfers.filter((transfer) => transfer.state === "REQUESTED").map((transfer) => (
              <div key={transfer.id} className="rounded-xl border border-amber-300 bg-amber-50 p-4">
                <p className="font-bold text-slate-950">Repository migration requested</p>
                <p className="mt-1 text-sm text-slate-700">An administrator requested that your record custody move to another repository.</p>
                <button onClick={async () => { try { const updated = await api.authorizeTransfer(transfer.id, "PATIENT_APPROVED_IN_PORTAL"); setTransfers((items) => items.map((item) => item.id === updated.id ? updated : item)); setMigrationMessage("Migration authorized. The administrator can now complete the controlled transfer."); } catch (reason: unknown) { setMigrationMessage(reason instanceof Error ? reason.message : "Unable to authorize migration"); } }} className="mt-3 rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white">Authorize repository move</button>
              </div>
            ))}
          </div>
          {migrationMessage && <p className="mt-3 text-sm font-semibold text-slate-700">{migrationMessage}</p>}
        </Card>
      )}

      {patient && (
        <Card title="Additional identity identifier">
          <div className="space-y-3">
            <p className="text-sm text-slate-700">Aadhaar is optional. It is encrypted in the identity database, and only you can manage it here. It is not sent to doctors or included in clinical FHIR records.</p>
            <p className="text-sm font-semibold text-slate-800">Current status: {aadhaarStatus?.has_aadhaar ? `Saved (${aadhaarStatus.masked_value})` : "Not added"}</p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input type="password" inputMode="numeric" autoComplete="off" maxLength={12} value={aadhaarNumber} onChange={(e) => setAadhaarNumber(e.target.value.replace(/\D/g, "").slice(0, 12))} placeholder="Enter 12-digit Aadhaar number" className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <button onClick={() => void saveAadhaar()} disabled={aadhaarNumber.length !== 12} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">Save Aadhaar</button>
            </div>
            {aadhaarMessage && <p className="text-sm text-slate-700">{aadhaarMessage}</p>}
            <p className="text-xs text-slate-500">HealthNet checks only the 12-digit format. No UIDAI authentication or verification is performed.</p>
          </div>
        </Card>
      )}

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Where is my medical record?">
          {currentLocation ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
              <p className="text-sm text-slate-600">Current authoritative repository</p>
              <p className="mt-1 text-2xl font-bold text-slate-950">{currentLocation.repository_name}</p>
              <p className="mt-1 text-sm font-semibold text-slate-700">{currentLocation.repository_code} · {currentLocation.jurisdiction}</p>
              <p className="mt-2 text-sm text-slate-700">HealthNet retrieves your clinical record from this repository only. Your Health ID stays the same if you move.</p>
            </div>
          ) : (
            <p className="text-sm text-slate-600">No current clinical repository assignment is available.</p>
          )}
        </Card>

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
                Enter the doctor's HealthNet Provider ID from their Doctor Workspace.
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
          {consents.length > 0 ? (
            <div className="mt-4 space-y-3">
              <h3 className="font-bold text-slate-950">Access granted to providers</h3>
              {consents.map((consent) => (
                <div key={consent.id} className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0 text-sm">
                    <p className="font-semibold text-slate-950">{consent.grantee_type}: {consent.grantee_id}</p>
                    <p className="text-slate-600">Purpose: {consent.purpose} · Scopes: {consent.scopes.join(", ")}</p>
                    <p className="text-slate-600">Status: <span className={consent.status === "ACTIVE" ? "font-bold text-emerald-700" : "font-bold text-slate-500"}>{consent.status}</span></p>
                    {consent.valid_until && <p className="text-slate-500">Valid until {new Date(consent.valid_until).toLocaleString()}</p>}
                    {consent.revoked_at && <p className="text-slate-500">Revoked {new Date(consent.revoked_at).toLocaleString()}</p>}
                  </div>
                  {consent.status === "ACTIVE" && (
                    <button onClick={() => void revokeConsent(consent.id)} className="shrink-0 rounded-lg border border-red-300 px-3 py-2 text-sm font-bold text-red-700 hover:bg-red-50">Revoke access</button>
                  )}
                </div>
              ))}
            </div>
          ) : <p className="mt-4 text-sm text-slate-600">No consent records found. Grant access to a trusted provider above.</p>}
          {emergency !== null && <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(emergency, null, 2)}</pre>}
          {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        </Card>
      </div>
    </PortalShell>
  );
}
