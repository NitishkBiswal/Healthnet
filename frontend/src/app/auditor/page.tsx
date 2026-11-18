"use client";

import { useEffect, useState } from "react";

import { api, type AuditEvent, type DuplicateReview } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function AuditorPortal() {
  const [healthId, setHealthId] = useState("");
  const [events, setEvents] = useState<unknown>(null);
  const [integrity, setIntegrity] = useState<unknown>(null);
  const [reviews, setReviews] = useState<DuplicateReview[]>([]);
  const [importAudits, setImportAudits] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");

  async function loadReviews() {
    try {
      setReviews(await api.duplicateReviews());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Could not load duplicate reviews");
    }
  }

  useEffect(() => {
    void loadReviews();
    api.importedRecordAudits().then(setImportAudits).catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load import audit events"));
  }, []);

  async function audit() {
    setError("");
    try {
      setEvents(await api.audits(healthId));
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
      setError(reason instanceof Error ? reason.message : "Could not update review");
    }
  }

  return (
    <PortalShell requiredRole="auditor" title="Auditor Portal" description="Identity decisions, audit trails and trust integrity.">
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Identity & profile change reviews">
          {reviews.length === 0 ? (
            <p className="text-sm text-slate-600">No duplicate reviews are waiting.</p>
          ) : (
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
                        <button onClick={() => decide(review.id, "APPROVED_PROFILE_UPDATE")} className="rounded-lg bg-slate-950 px-3 py-2 text-xs font-bold text-white">Approve profile update</button>
                        <button onClick={() => decide(review.id, "REJECTED")} className="rounded-lg border border-slate-400 bg-white px-3 py-2 text-xs font-bold text-slate-900">Reject profile update</button>
                      </> : <>
                        <button onClick={() => decide(review.id, "APPROVED_DUPLICATE")} className="rounded-lg bg-slate-950 px-3 py-2 text-xs font-bold text-white">Approve duplicate</button>
                        <button onClick={() => decide(review.id, "REJECTED")} className="rounded-lg border border-slate-400 bg-white px-3 py-2 text-xs font-bold text-slate-900">Reject match</button>
                      </>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Patient audit trail">
          <div className="flex gap-2">
            <Field value={healthId} onChange={(event) => setHealthId(event.target.value)} placeholder="Health ID" />
            <button onClick={audit} className="rounded-lg bg-slate-950 px-4 text-sm font-bold text-white">Inspect</button>
          </div>
          {events !== null && <pre className="mt-4 max-h-[500px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(events, null, 2)}</pre>}
        </Card>

        <Card title="Imported medical record audit">
          <p className="mb-3 text-sm text-slate-700">Read-only history of records imported by administrators. Auditors can inspect source, actor, resource identifiers and file hash; they cannot change clinical records.</p>
          {importAudits.length === 0 ? <p className="text-sm text-slate-600">No imported-record events found.</p> : (
            <div className="max-h-[420px] space-y-2 overflow-auto">
              {importAudits.map((event) => (
                <div key={event.id} className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-xs">
                  <p className="font-bold text-slate-950">{event.health_id} · {event.action}</p>
                  <p className="text-slate-700">Actor: {event.actor_id} · {event.created_at}</p>
                  <p className="text-slate-700">{JSON.stringify(event.payload)}</p>
                  <p className="break-all text-slate-500">Hash: {event.event_hash}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
        <Card title="Trust ledger integrity">
          <button onClick={verify} className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-bold text-slate-950 hover:bg-cyan-400">Verify chain</button>
          {integrity !== null && <pre className="mt-4 rounded-lg bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(integrity, null, 2)}</pre>}
          {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        </Card>
      </div>
    </PortalShell>
  );
}
