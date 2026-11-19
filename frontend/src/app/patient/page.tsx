"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type Consent, type CurrentRecordLocation, type DuplicateReview, type Patient, type Repository, type Transfer } from "@/lib/api";
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
  const [transferDestinations, setTransferDestinations] = useState<Repository[]>([]);
  const [transferDestination, setTransferDestination] = useState("");
  const [transferReason, setTransferReason] = useState("");
  const [transferBusy, setTransferBusy] = useState(false);
  const [migrationMessage, setMigrationMessage] = useState("");
  const [profileForm, setProfileForm] = useState({ given_name: "", family_name: "", date_of_birth: "", sex: "", phone: "", email: "", address: "" });
  const [profileMessage, setProfileMessage] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [editingProfile, setEditingProfile] = useState(false);
  const [medicalRecords, setMedicalRecords] = useState<Record<string, unknown> | null>(null);
  const [medicalRecordsError, setMedicalRecordsError] = useState("");
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"profile" | "consents" | "records" | "transfer">("profile");

  useEffect(() => {
    void api.myPatient().then(async (value) => {
      setPatient(value);
      setProfileForm({ given_name: value.given_name ?? "", family_name: value.family_name ?? "", date_of_birth: value.date_of_birth ?? "", sex: value.sex ?? "", phone: value.phone ?? "", email: value.email ?? "", address: value.address ?? "" });
      setRecordsLoading(true);
      try { setMedicalRecords(await api.myMedicalRecords()); }
      catch (reason: unknown) { setMedicalRecordsError(reason instanceof Error ? reason.message : "Unable to load medical records"); }
      finally { setRecordsLoading(false); }
      try { setConsents(await api.consents(value.display_health_id)); } catch {}
      try { setCurrentLocation(await api.currentRecordLocation(value.display_health_id)); } catch {}
      try { setTransfers(await api.myTransfers()); } catch {}
      try { setTransferDestinations(await api.transferDestinations()); } catch {}
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

  async function saveProfile() {
    setProfileMessage("");
    if (!profileForm.given_name.trim() || !profileForm.family_name.trim() || !profileForm.date_of_birth) {
      setProfileMessage("Given name, family name and date of birth are required.");
      return;
    }
    setProfileSaving(true);
    try {
      const result = await api.updateMyProfile({
        given_name: profileForm.given_name.trim(), family_name: profileForm.family_name.trim(),
        date_of_birth: profileForm.date_of_birth, sex: profileForm.sex.trim() || undefined,
        phone: profileForm.phone.trim() || undefined, email: profileForm.email.trim() || undefined,
        address: profileForm.address.trim() || undefined,
      });
      if (result.outcome === "PENDING_REVIEW") {
        setProfileMessage("A possible duplicate was detected. Your current profile is unchanged while the Auditor reviews this update.");
        setReviews(await api.myDuplicateReviews());
      } else if (result.patient) {
        setPatient(result.patient);
        setProfileForm({ given_name: result.patient.given_name, family_name: result.patient.family_name, date_of_birth: result.patient.date_of_birth, sex: result.patient.sex ?? "", phone: result.patient.phone ?? "", email: result.patient.email ?? "", address: result.patient.address ?? "" });
        setProfileMessage("Your profile has been updated.");
      }
      setEditingProfile(false);
    } catch (reason: unknown) {
      setProfileMessage(reason instanceof Error ? reason.message : "Unable to update profile.");
    } finally { setProfileSaving(false); }
  }

  async function refreshRepositoryTransferData() {
    if (!patient) return;
    setMigrationMessage("");
    try {
      const [location, history, destinations, records] = await Promise.all([
        api.currentRecordLocation(patient.display_health_id),
        api.myTransfers(),
        api.transferDestinations(),
        api.myMedicalRecords(),
      ]);
      setCurrentLocation(location);
      setTransfers(history);
      setTransferDestinations(destinations);
      setMedicalRecords(records);
      setMedicalRecordsError("");
      setMigrationMessage("Repository assignment, transfer history and medical records refreshed.");
    } catch (reason: unknown) {
      setMigrationMessage(reason instanceof Error ? reason.message : "Unable to refresh repository information.");
    }
  }

  async function requestRepositoryTransfer() {
    if (!transferDestination) {
      setMigrationMessage("Select a destination repository.");
      return;
    }
    if (transferReason.trim().length < 10) {
      setMigrationMessage("Please provide a reason of at least 10 characters.");
      return;
    }
    setTransferBusy(true);
    setMigrationMessage("");
    try {
      const created = await api.createMyTransfer({
        destination_repository_id: transferDestination,
        reason: transferReason.trim(),
      });
      setTransfers((items) => [created, ...items]);
      setTransferReason("");
      setMigrationMessage("Transfer request submitted. Review the request below and authorize it to continue.");
    } catch (reason: unknown) {
      setMigrationMessage(reason instanceof Error ? reason.message : "Unable to submit repository transfer.");
    } finally {
      setTransferBusy(false);
    }
  }

  async function authorizeRepositoryTransfer(transferId: string) {
    setMigrationMessage("");
    try {
      const updated = await api.authorizeTransfer(transferId, "PATIENT_APPROVED_IN_PORTAL");
      setTransfers((items) => items.map((item) => item.id === updated.id ? updated : item));
      setMigrationMessage(
        updated.state === "PENDING_AUDITOR_REVIEW"
          ? "You authorized this move. Because your account has reached the transfer review threshold, an Auditor must approve it before migration."
          : "You authorized this move. It is now waiting for the HealthNet administrator to complete the verified transfer."
      );
    } catch (reason: unknown) {
      setMigrationMessage(reason instanceof Error ? reason.message : "Unable to authorize repository transfer.");
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
                <p className="font-semibold">{review.review_type === "PROFILE_UPDATE" ? "Profile update review" : "Duplicate identity review"}: {review.status}</p>
                <p className="mt-1">Confidence {review.confidence.toFixed(2)} · submitted {new Date(review.created_at).toLocaleString()}</p>
                <p className="mt-1">{review.review_type === "PROFILE_UPDATE" ? "Your current profile remains unchanged until the Auditor decides on the proposed changes." : "The Auditor Portal is reviewing this identity match."}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {patient && (
        <nav aria-label="Patient portal tabs" className="mb-5 grid grid-cols-2 md:grid-cols-4 gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-sm">
          <button type="button" role="tab" aria-selected={activeTab === "profile"} onClick={() => setActiveTab("profile")} className={activeTab === "profile" ? "rounded-lg bg-slate-900 px-2 py-3 text-sm font-semibold text-white" : "rounded-lg px-2 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-100"}>Profile</button>
          <button type="button" role="tab" aria-selected={activeTab === "consents"} onClick={() => setActiveTab("consents")} className={activeTab === "consents" ? "rounded-lg bg-slate-900 px-2 py-3 text-sm font-semibold text-white" : "rounded-lg px-2 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-100"}>Grant & revoke consents</button>
          <button type="button" role="tab" aria-selected={activeTab === "records"} onClick={() => setActiveTab("records")} className={activeTab === "records" ? "rounded-lg bg-slate-900 px-2 py-3 text-sm font-semibold text-white" : "rounded-lg px-2 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-100"}>Medical records</button>
          <button type="button" role="tab" aria-selected={activeTab === "transfer"} onClick={() => setActiveTab("transfer")} className={activeTab === "transfer" ? "rounded-lg bg-slate-900 px-2 py-3 text-sm font-semibold text-white" : "rounded-lg px-2 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-100"}>Transfer repository</button>
        </nav>
      )}

      {patient && activeTab === "transfer" && (
        <div className="space-y-5">
          <Card title="Transfer your medical records to another repository">
            <p className="text-sm text-slate-600">Your Health ID never changes. After a verified transfer, the destination becomes the single authoritative repository used for future record access and updates.</p>
            {currentLocation && (
              <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">Current authoritative repository</p>
                <p className="mt-1 text-lg font-bold text-slate-950">{currentLocation.repository_name}</p>
                <p className="text-sm text-slate-700">{currentLocation.repository_code} · {currentLocation.jurisdiction}</p>
              </div>
            )}
            <div className="mt-4 grid gap-3">
              <label className="text-sm font-semibold text-slate-800">Destination repository
                <select value={transferDestination} onChange={(event) => setTransferDestination(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2">
                  <option value="">Choose a destination</option>
                  {transferDestinations.map((repository) => <option key={repository.id} value={repository.id}>{repository.name} ({repository.code})</option>)}
                </select>
              </label>
              <label className="text-sm font-semibold text-slate-800">Reason for transfer
                <textarea value={transferReason} onChange={(event) => setTransferReason(event.target.value)} rows={3} maxLength={1000} placeholder="For example: I have permanently moved to Karnataka and want my medical records managed by the Karnataka repository." className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" />
              </label>
              <p className="text-xs text-slate-500">A clear reason is required and is retained in the transfer audit trail.</p>
              <div>
                <button type="button" disabled={transferBusy || !transferDestination || transferReason.trim().length < 10} onClick={() => void requestRepositoryTransfer()} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">{transferBusy ? "Submitting..." : "Request repository transfer"}</button>
              </div>
            </div>
            {migrationMessage && <p role="status" className="mt-3 rounded-lg bg-cyan-50 p-3 text-sm font-semibold text-slate-800">{migrationMessage}</p>}
          </Card>

          <div className="flex justify-end">
            <button type="button" onClick={() => void refreshRepositoryTransferData()} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700">Refresh repository status</button>
          </div>
          <Card title="Transfer history & approvals">
            {transfers.length === 0 ? <p className="text-sm text-slate-600">No repository transfers have been requested yet.</p> : (
              <div className="space-y-3">
                {transfers.map((transfer) => (
                  <div key={transfer.id} className="rounded-xl border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-bold text-slate-950">Repository transfer</p>
                      <span className={transfer.state === "COMPLETED" ? "rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800" : transfer.state === "REJECTED" || transfer.state === "FAILED" ? "rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-800" : "rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900"}>{transfer.state.replaceAll("_", " ")}</span>
                    </div>
                    <p className="mt-2 text-sm text-slate-700">Reason: {transfer.reason}</p>
                    <p className="mt-1 text-xs text-slate-500">Requested {new Date(transfer.created_at).toLocaleString()} · Transfer ID: {transfer.id}</p>
                    {transfer.review_required && <p className="mt-2 text-sm font-semibold text-amber-800">Auditor review: {transfer.review_status}</p>}
                    {transfer.state === "REQUESTED" && (
                      <button type="button" onClick={() => void authorizeRepositoryTransfer(transfer.id)} className="mt-3 rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white">Review & authorize this transfer</button>
                    )}
                    {transfer.state === "PENDING_AUDITOR_REVIEW" && <p className="mt-3 text-sm text-amber-800">Your authorization is recorded. An Auditor must review this transfer before it can proceed.</p>}
                    {transfer.state === "PATIENT_AUTHORIZED" || transfer.state === "TRANSFER_AUTH_ISSUED" ? <p className="mt-3 text-sm text-cyan-800">Patient authorization complete. Waiting for the administrator to run and verify the transfer.</p> : null}
                    {transfer.error_message && <p className="mt-2 text-sm text-red-700">{transfer.error_message}</p>}
                    {transfer.state === "REJECTED" && transfer.reviewer_note && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900"><p className="font-bold">Transfer rejected</p><p className="mt-1"><strong>Reason:</strong> {transfer.reviewer_note}</p>{transfer.reviewed_at && <p className="mt-1 text-xs text-red-800">Decision recorded {new Date(transfer.reviewed_at).toLocaleString()}</p>}</div>}
                    {transfer.state !== "REJECTED" && transfer.reviewer_note && <p className="mt-2 text-sm text-slate-600">Review note: {transfer.reviewer_note}</p>}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {patient && activeTab === "profile" && (
        <Card title="Personal profile">
          <p className="mb-5 text-sm text-slate-600">Your registered details. Select Edit profile to request a change.</p>
          <div className="grid gap-x-8 gap-y-5 md:grid-cols-2">
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Given name</p><p className="mt-1 text-base font-semibold text-slate-900">{patient.given_name || "—"}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Family name</p><p className="mt-1 text-base font-semibold text-slate-900">{patient.family_name || "—"}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Date of birth</p><p className="mt-1 text-base font-semibold text-slate-900">{patient.date_of_birth ? new Date(patient.date_of_birth + "T00:00:00").toLocaleDateString() : "—"}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sex</p><p className="mt-1 text-base font-semibold text-slate-900">{patient.sex || "—"}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Phone</p><p className="mt-1 text-base font-semibold text-slate-900">{patient.phone || "—"}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Email</p><p className="mt-1 text-base font-semibold text-slate-900">{patient.email || "—"}</p></div>
            <div className="md:col-span-2"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Address</p><p className="mt-1 whitespace-pre-wrap text-base font-semibold text-slate-900">{patient.address || "—"}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Health ID</p><p className="mt-1 text-base font-bold text-cyan-900">{patient.display_health_id}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Jurisdiction</p><p className="mt-1 text-base font-semibold text-slate-900">{patient.issuing_jurisdiction}</p></div>
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4">
            <button type="button" onClick={() => { setProfileMessage(""); setProfileForm({ given_name: patient.given_name ?? "", family_name: patient.family_name ?? "", date_of_birth: patient.date_of_birth ?? "", sex: patient.sex ?? "", phone: patient.phone ?? "", email: patient.email ?? "", address: patient.address ?? "" }); setEditingProfile(true); }} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white">Edit profile</button>
            {profileMessage && <p role="status" className="text-sm text-slate-700">{profileMessage}</p>}
          </div>
        </Card>
      )}

      {editingProfile && patient && (
        <div role="presentation" className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/60 p-4">
          <section role="dialog" aria-modal="true" aria-labelledby="edit-profile-title" className="my-auto w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div><h2 id="edit-profile-title" className="text-xl font-bold text-slate-950">Edit personal profile</h2><p className="mt-1 text-sm text-slate-600">Submit your proposed changes. Possible duplicate matches are sent to an Auditor for review.</p></div>
              <button type="button" onClick={() => setEditingProfile(false)} className="rounded-lg border border-slate-300 px-3 py-1 text-sm font-semibold text-slate-700">Close</button>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block text-sm font-medium text-slate-700">Given name<input value={profileForm.given_name} onChange={(e) => setProfileForm((v) => ({ ...v, given_name: e.target.value }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label>
              <label className="block text-sm font-medium text-slate-700">Family name<input value={profileForm.family_name} onChange={(e) => setProfileForm((v) => ({ ...v, family_name: e.target.value }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label>
              <label className="block text-sm font-medium text-slate-700">Date of birth<input type="date" value={profileForm.date_of_birth} onChange={(e) => setProfileForm((v) => ({ ...v, date_of_birth: e.target.value }))} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label>
              <label className="block text-sm font-medium text-slate-700">Sex<input value={profileForm.sex} onChange={(e) => setProfileForm((v) => ({ ...v, sex: e.target.value }))} placeholder="Not provided" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label>
              <label className="block text-sm font-medium text-slate-700">Phone<input value={profileForm.phone} onChange={(e) => setProfileForm((v) => ({ ...v, phone: e.target.value }))} placeholder="Not provided" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label>
              <label className="block text-sm font-medium text-slate-700">Email<input type="email" value={profileForm.email} onChange={(e) => setProfileForm((v) => ({ ...v, email: e.target.value }))} placeholder="Not provided" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label>
              <label className="block text-sm font-medium text-slate-700 md:col-span-2">Address<textarea value={profileForm.address} onChange={(e) => setProfileForm((v) => ({ ...v, address: e.target.value }))} placeholder="Not provided" rows={3} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" /></label>
            </div>
            {profileMessage && <p role="alert" className="mt-3 text-sm text-red-700">{profileMessage}</p>}
            <div className="mt-6 flex justify-end gap-3">
              <button type="button" onClick={() => setEditingProfile(false)} disabled={profileSaving} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">Cancel</button>
              <button type="button" onClick={() => void saveProfile()} disabled={profileSaving} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{profileSaving ? "Submitting…" : "Submit changes"}</button>
            </div>
          </section>
        </div>
      )}

      {patient && activeTab === "records" && (
        <Card title="My Medical Records">
          <div className="space-y-4">
            {recordsLoading && <p className="text-sm text-slate-600">Loading your records from your current repository…</p>}
            {medicalRecordsError && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{medicalRecordsError}</p>}
            {medicalRecords && (() => {
              const records = Array.isArray(medicalRecords.records) ? medicalRecords.records as { resource_type?: string; resource?: Record<string, unknown> }[] : [];
              const dateOf = (r: Record<string, unknown>) => String(r.effectiveDateTime ?? r.recordedDate ?? r.onsetDateTime ?? r.authoredOn ?? r.date ?? "");
              const sorted = [...records].sort((a,b) => dateOf(b.resource ?? {}).localeCompare(dateOf(a.resource ?? {})));
              const conditions = sorted.filter(item => item.resource_type === "Condition");
              const observations = sorted.filter(item => item.resource_type === "Observation");
              const medications = sorted.filter(item => item.resource_type === "MedicationRequest" || item.resource_type === "MedicationStatement");
              const labelOf = (r: Record<string, unknown>) => {
                const code = r.code as { text?: string; coding?: { display?: string }[] } | undefined;
                return code?.text ?? code?.coding?.find(c => c.display)?.display ?? String(r.resourceType ?? "Clinical record");
              };
              const dateLabel = (r: Record<string, unknown>) => { const value = dateOf(r); return value ? new Date(value).toLocaleString() : "Date not recorded"; };
              const renderGroup = (title: string, items: typeof sorted) => <section key={title}>
                <h3 className="mb-2 font-bold text-slate-950">{title} ({items.length})</h3>
                {items.length === 0 ? <p className="text-sm text-slate-500">No records found.</p> : <div className="space-y-2">{items.map((item, index) => {
                  const resource = item.resource ?? {};
                  const value = resource.valueQuantity as { value?: number; unit?: string } | undefined;
                  const components = Array.isArray(resource.component) ? resource.component as { code?: { coding?: { display?: string }[] }; valueQuantity?: { value?: number; unit?: string } }[] : [];
                  return <details key={String(resource.id ?? index)} className="rounded-lg border border-slate-200 p-3">
                    <summary className="cursor-pointer text-sm font-semibold text-slate-900">{labelOf(resource)} <span className="font-normal text-slate-500">· {dateLabel(resource)}</span></summary>
                    <div className="mt-2 space-y-1 text-sm text-slate-700">
                      {value && <p>Result: {value.value ?? "—"} {value.unit ?? ""}</p>}
                      {components.map((component, i) => <p key={i}>{component.code?.coding?.[0]?.display ?? "Measurement"}: {component.valueQuantity?.value ?? "—"} {component.valueQuantity?.unit ?? ""}</p>)}
                      <p>Status: {String((resource.clinicalStatus as { coding?: { display?: string; code?: string }[] } | undefined)?.coding?.[0]?.display ?? (resource.clinicalStatus as { coding?: { display?: string; code?: string }[] } | undefined)?.coding?.[0]?.code ?? resource.status ?? "Not specified")}</p>
                      <details className="mt-2"><summary className="cursor-pointer text-xs font-semibold text-cyan-800">View original FHIR details</summary><pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(resource, null, 2)}</pre></details>
                    </div>
                  </details>;
                })}</div>}
              </section>;
              return <>
                <div className="rounded-lg bg-cyan-50 p-3 text-sm text-slate-700">Health ID: <strong>{String(medicalRecords.health_id ?? patient.display_health_id)}</strong> · Repository: <strong>{String((medicalRecords.current_repository as { name?: string } | null)?.name ?? "Unavailable")}</strong> · Status: <strong>{String(medicalRecords.completeness ?? "Unknown")}</strong></div>
                {renderGroup("Chronic conditions & medical problems", conditions)}
                {renderGroup("Observations & laboratory results", observations)}
                {renderGroup("Medications", medications)}
                {renderGroup("Other clinical records", sorted.filter(item => !["Condition", "Observation", "MedicationRequest", "MedicationStatement"].includes(item.resource_type ?? "") && item.resource_type !== "Patient"))}
                {Array.isArray(medicalRecords.errors) && (medicalRecords.errors as string[]).length > 0 && <p className="text-xs text-amber-700">Some record types could not be loaded: {(medicalRecords.errors as string[]).join("; ")}</p>}
              </>;
            })()}
            {medicalRecords && Array.isArray(medicalRecords.records) && (medicalRecords.records as unknown[]).length === 0 && !recordsLoading && <p className="text-sm text-slate-600">No clinical records were found in your current repository.</p>}
          </div>
        </Card>
      )}

      {activeTab === "profile" && <div className="mt-5 grid gap-5 lg:grid-cols-2">
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
      </div>}

      {activeTab === "consents" && <Card title="Grant & revoke doctor access">
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
        </Card>}
    </PortalShell>
  );
}
