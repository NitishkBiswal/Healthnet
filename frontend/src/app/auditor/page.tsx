"use client";

import { useEffect, useState } from "react";

import { api, type AuditEvent, type DuplicateReview, type Transfer } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

type AuditorTab = "overview" | "identity" | "transfers" | "patient-audit" | "emergency-access" | "imports" | "integrity";

const tabs: { id: AuditorTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "identity", label: "Identity Reviews" },
  { id: "transfers", label: "Transfer Reviews" },
  { id: "patient-audit", label: "Patient Audit Trail" },
  { id: "emergency-access", label: "Emergency Access" },
  { id: "imports", label: "Import Audit" },
  { id: "integrity", label: "Trust Integrity" },
];

function EventCard({ event }: { event: AuditEvent }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-bold text-slate-950">{event.health_id ?? "System event"} · {event.action}</p>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">{event.event_type}</span>
      </div>
      <p className="mt-2 text-xs text-slate-600">Actor: {event.actor_id} · {new Date(event.created_at).toLocaleString()}</p>
      <details className="mt-3">
        <summary className="cursor-pointer text-xs font-semibold text-cyan-800">View event payload</summary>
        <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(event.payload, null, 2)}</pre>
      </details>
      <p className="mt-2 break-all text-xs text-slate-500">Event hash: {event.event_hash}</p>
    </article>
  );
}

export default function AuditorPortal() {
  const [activeTab, setActiveTab] = useState<AuditorTab>("overview");
  const [healthId, setHealthId] = useState("");
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [integrity, setIntegrity] = useState<{ valid: boolean; entries_checked: number } | null>(null);
  const [reviews, setReviews] = useState<DuplicateReview[]>([]);
  const [transferReviews, setTransferReviews] = useState<Transfer[]>([]);
  const [transferRejectionReasons, setTransferRejectionReasons] = useState<Record<string, string>>({});
  const [importAudits, setImportAudits] = useState<AuditEvent[]>([]);
  const [emergencyAccessEvents, setEmergencyAccessEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadReviews() {
    try {
      setReviews(await api.duplicateReviews());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not load identity reviews");
    }
  }

  async function loadTransferReviews() {
    try {
      setTransferReviews(await api.auditorTransferReviews());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not load repository transfer reviews");
    }
  }

  async function loadEmergencyAccessEvents() {
    try {
      setEmergencyAccessEvents(await api.emergencyAccessAudits());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not load emergency-access audit events");
    }
  }

  async function loadImportAudits() {
    try {
      setImportAudits(await api.importedRecordAudits());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not load import audit events");
    }
  }

  async function refreshAll() {
    setError("");
    setBusy(true);
    await Promise.all([loadReviews(), loadTransferReviews(), loadImportAudits(), loadEmergencyAccessEvents()]);
    setBusy(false);
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  async function audit() {
    if (!healthId.trim()) {
      setError("Enter a patient Health ID first.");
      return;
    }
    setError("");
    try {
      setEvents(await api.audits(healthId.trim()));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Audit access denied");
    }
  }

  async function verify() {
    setError("");
    try {
      setIntegrity(await api.verifyLedger());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Ledger verification failed");
    }
  }

  async function decide(id: string, decision: "APPROVED_DUPLICATE" | "APPROVED_PROFILE_UPDATE" | "REJECTED") {
    setError("");
    try {
      await api.decideDuplicateReview(id, decision);
      await loadReviews();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not update identity review");
    }
  }

  async function decideTransfer(id: string, decision: "APPROVE" | "REJECT") {
    setError("");
    const note = (transferRejectionReasons[id] ?? "").trim();
    if (decision === "REJECT" && note.length < 10) {
      setError("Enter a rejection reason of at least 10 characters.");
      return;
    }
    try {
      await api.reviewTransfer(
        id,
        decision,
        decision === "APPROVE"
          ? "Transfer reason and history reviewed; approved for migration."
          : note,
      );
      setTransferRejectionReasons((items) => ({ ...items, [id]: "" }));
      await loadTransferReviews();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not update transfer review");
    }
  }

  const pendingIdentityReviews = reviews.filter((review) => review.status === "PENDING").length;
  const pendingTransferReviews = transferReviews.length;
  const totalAuditEvents = importAudits.length + (events?.length ?? 0);

  return (
    <PortalShell requiredRole="auditor" title="Auditor Portal" description="Independent oversight of identity decisions, repository transfers, audit trails and trust integrity.">
      <div className="mb-5 flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-sm">
        {tabs.map((tab) => {
          const count = tab.id === "identity" ? pendingIdentityReviews : tab.id === "transfers" ? pendingTransferReviews : 0;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-lg px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-slate-950 text-white shadow" : "text-slate-700 hover:bg-slate-100"}`}
            >
              {tab.label}
              {count > 0 && <span className={`ml-2 rounded-full px-2 py-0.5 text-xs ${activeTab === tab.id ? "bg-white/20 text-white" : "bg-amber-100 text-amber-900"}`}>{count}</span>}
            </button>
          );
        })}
        <button type="button" onClick={() => void refreshAll()} disabled={busy} className="ml-auto rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
          {busy ? "Refreshing..." : "Refresh data"}
        </button>
      </div>

      {activeTab === "overview" && (
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Pending identity reviews", value: pendingIdentityReviews, detail: "Potential duplicate or profile-change cases" },
              { label: "Pending transfer reviews", value: pendingTransferReviews, detail: "Transfers requiring independent approval" },
              { label: "Imported-record audit events", value: importAudits.length, detail: "Read-only import history currently available" },
              { label: "Patient audit lookup", value: "Available", detail: "Inspect events by patient Health ID" },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">{item.label}</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-slate-950">{item.value}</p>
                <p className="mt-1 text-xs text-slate-500">{item.detail}</p>
              </div>
            ))}
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Reviews requiring attention">
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-lg bg-slate-50 p-3">
                  <div><p className="font-semibold text-slate-900">Identity and profile changes</p><p className="text-xs text-slate-600">Review possible duplicate identities and profile updates.</p></div>
                  <button type="button" onClick={() => setActiveTab("identity")} className="text-sm font-bold text-cyan-800 underline">Open</button>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-slate-50 p-3">
                  <div><p className="font-semibold text-slate-900">Repository transfers</p><p className="text-xs text-slate-600">Independently review exceptional transfer requests.</p></div>
                  <button type="button" onClick={() => setActiveTab("transfers")} className="text-sm font-bold text-cyan-800 underline">Open</button>
                </div>
              </div>
            </Card>
            <Card title="Audit and integrity tools">
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-lg bg-slate-50 p-3">
                  <div><p className="font-semibold text-slate-900">Patient audit trail</p><p className="text-xs text-slate-600">Search audit events using a Health ID.</p></div>
                  <button type="button" onClick={() => setActiveTab("patient-audit")} className="text-sm font-bold text-cyan-800 underline">Open</button>
                </div>
                <div className="flex items-center justify-between rounded-lg bg-slate-50 p-3">
                  <div><p className="font-semibold text-slate-900">Trust ledger verification</p><p className="text-xs text-slate-600">Verify the ledger hash chain.</p></div>
                  <button type="button" onClick={() => setActiveTab("integrity")} className="text-sm font-bold text-cyan-800 underline">Open</button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {activeTab === "identity" && (
        <Card title="Identity and profile change reviews">
          <p className="mb-4 text-sm text-slate-600">Review possible duplicate patient identities and profile changes. Decisions are recorded through the Auditor review workflow.</p>
          {reviews.length === 0 ? <p className="text-sm text-slate-600">No identity reviews are available.</p> : (
            <div className="space-y-4">
              {reviews.map((review) => (
                <div key={review.id} className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-bold">{review.proposed_given_name} {review.proposed_family_name}</p>
                    <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold">{review.status}</span>
                  </div>
                  {review.review_type === "PROFILE_UPDATE" && <p className="mt-2">Patient Health ID: <strong>{review.target_health_id ?? review.target_patient_id ?? "—"}</strong></p>}
                  <p>Possible matching Health ID: <strong>{review.candidate_health_id ?? review.candidate_patient_id}</strong></p>
                  <p>Match confidence: <strong>{review.confidence.toFixed(2)}</strong></p>
                  <p>Proposed date of birth: {review.proposed_date_of_birth}</p>
                  {review.proposed_sex && <p>Proposed sex: {review.proposed_sex}</p>}
                  {review.proposed_email && <p>Proposed email: {review.proposed_email}</p>}
                  {review.proposed_phone && <p>Proposed phone: {review.proposed_phone}</p>}
                  {review.proposed_address && <p>Proposed address: {review.proposed_address}</p>}
                  {review.status === "PENDING" && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {review.review_type === "PROFILE_UPDATE" ? <>
                        <button type="button" onClick={() => void decide(review.id, "APPROVED_PROFILE_UPDATE")} className="rounded-lg bg-slate-950 px-3 py-2 text-xs font-bold text-white">Approve profile update</button>
                        <button type="button" onClick={() => void decide(review.id, "REJECTED")} className="rounded-lg border border-slate-400 bg-white px-3 py-2 text-xs font-bold text-slate-900">Reject profile update</button>
                      </> : <>
                        <button type="button" onClick={() => void decide(review.id, "APPROVED_DUPLICATE")} className="rounded-lg bg-slate-950 px-3 py-2 text-xs font-bold text-white">Approve duplicate</button>
                        <button type="button" onClick={() => void decide(review.id, "REJECTED")} className="rounded-lg border border-slate-400 bg-white px-3 py-2 text-xs font-bold text-slate-900">Reject match</button>
                      </>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {activeTab === "transfers" && (
        <Card title="Repository transfer reviews">
          <p className="mb-4 text-sm text-slate-600">Transfers beyond the normal patient transfer allowance require an independent Auditor decision. Review the patient's reason and previous completed transfer count before approval.</p>
          {transferReviews.length === 0 ? <p className="text-sm text-slate-600">No repository transfers are waiting for Auditor review.</p> : (
            <div className="space-y-3">
              {transferReviews.map((transfer) => (
                <div key={transfer.id} className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-bold text-slate-950">Health ID: {transfer.health_id}</p>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-amber-900">PENDING REVIEW</span>
                  </div>
                  <p className="mt-2 text-slate-800"><strong>Reason:</strong> {transfer.reason}</p>
                  <p className="mt-1 text-slate-700"><strong>Completed previous transfers:</strong> {transfer.completed_transfer_count ?? 0}</p>
                  <p className="mt-1 break-all text-xs text-slate-500">Transfer ID: {transfer.id}</p>
                  <p className="mt-1 text-xs text-slate-500">Submitted: {new Date(transfer.created_at).toLocaleString()}</p>
                  <label className="mt-3 block">
                    <span className="text-xs font-semibold text-slate-700">Rejection reason (visible to the patient)</span>
                    <textarea value={transferRejectionReasons[transfer.id] ?? ""} onChange={(event) => setTransferRejectionReasons((items) => ({ ...items, [transfer.id]: event.target.value }))} rows={2} maxLength={1000} placeholder="Explain why this transfer should not proceed (minimum 10 characters)." className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-3 text-sm text-slate-900" />
                  </label>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button type="button" onClick={() => void decideTransfer(transfer.id, "APPROVE")} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-bold text-white">Approve transfer</button>
                    <button type="button" disabled={(transferRejectionReasons[transfer.id] ?? "").trim().length < 10} onClick={() => void decideTransfer(transfer.id, "REJECT")} className="rounded-lg border border-red-300 bg-white px-3 py-2 text-xs font-bold text-red-700 disabled:cursor-not-allowed disabled:opacity-40">Reject transfer</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {activeTab === "patient-audit" && (
        <Card title="Patient audit trail">
          <p className="mb-3 text-sm text-slate-600">Enter a Health ID to inspect its recorded audit events. Event details are displayed read-only.</p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Field value={healthId} onChange={(event) => setHealthId(event.target.value)} placeholder="Patient Health ID" />
            <button type="button" onClick={() => void audit()} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white">Inspect patient</button>
          </div>
          {events !== null && <div className="mt-4 space-y-3">{events.length === 0 ? <p className="text-sm text-slate-600">No audit events were returned for this Health ID.</p> : events.map((event) => <EventCard key={event.id} event={event} />)}</div>}
        </Card>
      )}

      {activeTab === "emergency-access" && (
        <Card title="Emergency break-glass audit">
          <p className="mb-4 text-sm text-slate-600">Read-only oversight of emergency declarations and one-time chronic-condition summary views. Review the doctor, patient, justification, jurisdiction, access scope and timestamps. This tab does not grant access to clinical records.</p>
          {emergencyAccessEvents.length === 0 ? (
            <p className="text-sm text-slate-600">No emergency break-glass events have been recorded.</p>
          ) : (
            <div className="space-y-3">
              {emergencyAccessEvents.map((event) => <EventCard key={event.id} event={event} />)}
            </div>
          )}
          <button type="button" onClick={() => void loadEmergencyAccessEvents()} className="mt-4 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">Refresh emergency events</button>
        </Card>
      )}

      {activeTab === "imports" && (
        <Card title="Imported medical record audit">
          <p className="mb-4 text-sm text-slate-600">Read-only history of medical-record imports performed by administrators. Inspect the actor, patient, payload and event hash; auditors cannot edit imported clinical records.</p>
          {importAudits.length === 0 ? <p className="text-sm text-slate-600">No imported-record events found.</p> : (
            <div className="space-y-3">{importAudits.map((event) => <EventCard key={event.id} event={event} />)}</div>
          )}
        </Card>
      )}

      {activeTab === "integrity" && (
        <Card title="Trust ledger integrity">
          <p className="mb-4 text-sm text-slate-600">Run a read-only verification of the trust ledger hash chain.</p>
          <button type="button" onClick={() => void verify()} className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-bold text-slate-950 hover:bg-cyan-400">Verify ledger chain</button>
          {integrity !== null && (
            <div className={`mt-4 rounded-lg border p-4 ${integrity.valid ? "border-emerald-300 bg-emerald-50" : "border-red-300 bg-red-50"}`}>
              <p className="font-bold">{integrity.valid ? "Ledger integrity verified" : "Ledger integrity check failed"}</p>
              <p className="mt-1 text-sm">Entries checked: {integrity.entries_checked}</p>
            </div>
          )}
        </Card>
      )}

      {error && <p role="alert" className="mt-5 rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-800">{error}</p>}
    </PortalShell>
  );
}
