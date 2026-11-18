"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  api,
  type Consent,
  type DuplicateReview,
  type EmergencyProfile,
  type Patient,
  type PatientNotification,
  type ProvenanceResource,
} from "@/lib/api";
import { Card, PortalShell } from "@/components/portal-shell";

export default function PatientPortal() {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [reviews, setReviews] = useState<DuplicateReview[]>([]);
  const [consents, setConsents] = useState<Consent[]>([]);
  const [consentOffset, setConsentOffset] = useState(0);
  const [hasMoreConsents, setHasMoreConsents] = useState(false);
  const [emergency, setEmergency] = useState<EmergencyProfile | null>(null);
  const [profile, setProfile] = useState<Omit<EmergencyProfile, "health_id" | "updated_at">>({
    blood_group: "", allergies: [], medications: [], conditions: [], emergency_contacts: [],
  });
  const [notifications, setNotifications] = useState<PatientNotification[]>([]);
  const [provenance, setProvenance] = useState<ProvenanceResource[]>([]);
  const [consentToRevoke, setConsentToRevoke] = useState<Consent | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [error, setError] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [purpose, setPurpose] = useState("TREATMENT");
  const [scope, setScope] = useState("clinical");
  const [validUntil, setValidUntil] = useState("");
  const [consentMessage, setConsentMessage] = useState("");
  const [consentBusy, setConsentBusy] = useState(false);
  const [transferId, setTransferId] = useState("");
  const [transferAuthorizationReference, setTransferAuthorizationReference] = useState("");
  const [transferMessage, setTransferMessage] = useState("");
  const [transferBusy, setTransferBusy] = useState(false);

  useEffect(() => {
    let active = true;
    async function loadPortal() {
      try {
        const [value, duplicateReviews] = await Promise.all([
          api.myPatient(),
          api.myDuplicateReviews(),
        ]);
        if (!active) return;
        setPatient(value);
        setReviews(duplicateReviews);
        const [patientConsents, patientNotifications] = await Promise.all([
          api.consents(value.display_health_id, 0, 50),
          api.notifications(value.display_health_id),
        ]);
        if (active) {
          setConsents(patientConsents);
          setHasMoreConsents(patientConsents.length === 50);
          setNotifications(patientNotifications);
        }
      } catch (reason: unknown) {
        if (active) setError(reason instanceof Error ? reason.message : "Unable to load patient portal");
      }
    }
    void loadPortal();
    return () => { active = false; };
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
    setConsentBusy(true);
    setConsentMessage("");
    try {
      await api.revokeConsent(consent.id);
      setConsents((current) => current.map((item) => item.id === consent.id
        ? { ...item, status: "REVOKED", revoked_at: new Date().toISOString() }
        : item));
      setConsentMessage("Permission revoked successfully. The provider can no longer access this patient record.");
      setConsentToRevoke(null);
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
      const updatedConsents = await api.consents(patient.display_health_id, 0, 50);
      setConsents(updatedConsents);
      setConsentOffset(0);
      setHasMoreConsents(updatedConsents.length === 50);
    } catch (reason: unknown) {
      setConsentMessage(reason instanceof Error ? reason.message : "Unable to grant consent");
    }
  }

  async function loadEmergencyProfile() {
    if (!patient) return;
    setError("");
    try {
      const saved = await api.emergency(patient.display_health_id);
      setEmergency(saved);
      setProfile({
        blood_group: saved.blood_group ?? "",
        allergies: saved.allergies,
        medications: saved.medications,
        conditions: saved.conditions,
        emergency_contacts: saved.emergency_contacts,
      });
    } catch (reason: unknown) {
      const message = reason instanceof Error ? reason.message : "Unable to load emergency profile";
      if (message.includes("Emergency profile not found")) {
        setEmergency(null);
        setError("No emergency profile yet. Add the details below and save it.");
      } else {
        setError(message);
      }
    }
  }

  async function saveEmergencyProfile() {
    if (!patient) return;
    setSavingProfile(true);
    setError("");
    try {
      const saved = await api.saveEmergency(patient.display_health_id, profile);
      setEmergency(saved);
      setProfile({
        blood_group: saved.blood_group ?? "",
        allergies: saved.allergies,
        medications: saved.medications,
        conditions: saved.conditions,
        emergency_contacts: saved.emergency_contacts,
      });
      setError("");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to save emergency profile");
    } finally {
      setSavingProfile(false);
    }
  }

  async function loadMoreConsents() {
    if (!patient) return;
    const nextOffset = consentOffset + 50;
    try {
      const next = await api.consents(patient.display_health_id, nextOffset, 50);
      setConsents((current) => [...current, ...next]);
      setConsentOffset(nextOffset);
      setHasMoreConsents(next.length === 50);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load more consent records");
    }
  }

  async function loadProvenance() {
    if (!patient) return;
    try {
      setProvenance(await api.provenance(patient.display_health_id));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load record history");
    }
  }

  async function authorizeTransfer() {
    if (!transferId.trim() || !transferAuthorizationReference.trim()) {
      setTransferMessage("Enter the transfer ID and authorization reference.");
      return;
    }
    setTransferBusy(true);
    setTransferMessage("");
    try {
      const authorized = await api.authorizeTransfer(transferId.trim(), transferAuthorizationReference.trim());
      setTransferMessage(`Transfer ${authorized.id} authorized. Its current status is ${authorized.state}.`);
      setTransferAuthorizationReference("");
    } catch (reason: unknown) {
      setTransferMessage(reason instanceof Error ? reason.message : "Unable to authorize this transfer");
    } finally {
      setTransferBusy(false);
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
            <button onClick={() => run(async () => {
              const items = await api.consents(patient?.display_health_id || "", 0, 50);
              setConsentOffset(0);
              setHasMoreConsents(items.length === 50);
              return items;
            }, setConsents)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-50">
              View consent
            </button>
            <button onClick={() => void loadEmergencyProfile()} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-50">
              Load saved emergency profile
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
                        onClick={() => setConsentToRevoke(consent)}
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
          {hasMoreConsents && <button onClick={() => void loadMoreConsents()} className="mt-3 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">Load more consent records</button>}
          {patient && <div className="mt-5 border-t border-slate-200 pt-5">
            <h3 className="font-bold">Emergency health profile</h3>
            <p className="mt-1 text-sm text-slate-600">These details can help clinicians during an emergency. Keep them current.</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <input value={profile.blood_group ?? ""} onChange={(event) => setProfile((current) => ({ ...current, blood_group: event.target.value }))} placeholder="Blood group (optional)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <textarea value={profile.allergies.join("\n")} onChange={(event) => setProfile((current) => ({ ...current, allergies: event.target.value.split("\n").filter(Boolean) }))} placeholder="Allergies (one per line)" rows={3} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <textarea value={profile.medications.join("\n")} onChange={(event) => setProfile((current) => ({ ...current, medications: event.target.value.split("\n").filter(Boolean) }))} placeholder="Medications (one per line)" rows={3} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <textarea value={profile.conditions.join("\n")} onChange={(event) => setProfile((current) => ({ ...current, conditions: event.target.value.split("\n").filter(Boolean) }))} placeholder="Conditions (one per line)" rows={3} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <textarea value={profile.emergency_contacts.join("\n")} onChange={(event) => setProfile((current) => ({ ...current, emergency_contacts: event.target.value.split("\n").filter(Boolean) }))} placeholder="Emergency contacts (one per line)" rows={3} className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2" />
            </div>
            <button onClick={() => void saveEmergencyProfile()} disabled={savingProfile} className="mt-3 rounded-lg bg-cyan-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
              {savingProfile ? "Saving profile…" : "Save emergency profile"}
            </button>
            {emergency?.updated_at && <p className="mt-2 text-xs text-slate-600">Last saved {new Date(emergency.updated_at).toLocaleString()}</p>}
          </div>}
          {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        </Card>
      </div>
      {patient && <Card title="Authorize an EHR transfer">
        <p className="text-sm text-slate-700">Only authorize a transfer you expect and understand. Ask your administrator for its transfer ID, then enter an authorization reference to approve it.</p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <input value={transferId} onChange={(event) => setTransferId(event.target.value)} placeholder="Transfer ID" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input value={transferAuthorizationReference} onChange={(event) => setTransferAuthorizationReference(event.target.value)} placeholder="Authorization reference" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <button onClick={() => void authorizeTransfer()} disabled={transferBusy} className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
          {transferBusy ? "Authorizing…" : "Authorize transfer"}
        </button>
        {transferMessage && <p role="status" className="mt-2 text-sm text-slate-700">{transferMessage}</p>}
      </Card>}
      {notifications.length > 0 && <Card title="Privacy and emergency notifications">
        <ul className="space-y-2">
          {notifications.map((notification) => <li key={notification.id} className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm">
            <p className="font-semibold">{notification.message}</p>
            <time className="mt-1 block text-xs text-slate-600">{new Date(notification.created_at).toLocaleString()}</time>
          </li>)}
        </ul>
      </Card>}
      {patient && <Card title="My record history">
        <button onClick={() => void loadProvenance()} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">Load record history</button>
        {provenance.length > 0 && <ol className="mt-3 space-y-2 border-l-2 border-cyan-300 pl-4">
          {provenance.map((entry) => <li key={entry.id} className="text-sm">
            <span className="font-semibold">{entry.activity.coding?.[0]?.display ?? "Record change"}</span>
            <span className="ml-2 text-slate-600">{entry.target[0]?.reference} · {new Date(entry.recorded).toLocaleString()}</span>
          </li>)}
        </ol>}
      </Card>}
      {consentToRevoke && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" role="presentation">
        <section role="dialog" aria-modal="true" aria-labelledby="revoke-title" className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <h2 id="revoke-title" className="text-lg font-bold">Revoke provider access?</h2>
          <p className="mt-2 text-sm text-slate-700">Access for {consentToRevoke.grantee_id} will be stopped immediately.</p>
          <div className="mt-5 flex justify-end gap-3">
            <button onClick={() => setConsentToRevoke(null)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button disabled={consentBusy} onClick={() => void revokeConsent(consentToRevoke)} className="rounded-lg bg-red-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Revoke access</button>
          </div>
        </section>
      </div>}
    </PortalShell>
  );
}
