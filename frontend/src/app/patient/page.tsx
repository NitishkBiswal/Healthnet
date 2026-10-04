"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type DuplicateReview, type Patient } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function PatientPortal() {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [reviews, setReviews] = useState<DuplicateReview[]>([]);
  const [healthId, setHealthId] = useState("");
  const [consents, setConsents] = useState<unknown>(null);
  const [emergency, setEmergency] = useState<unknown>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void api.myPatient().then(setPatient).catch(() => {});
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

  return (
    <PortalShell
      requiredRole="patient"
      title="Patient Portal"
      description="Your Health ID, permissions and emergency profile."
    >
      <div className="mb-5 flex flex-wrap gap-3">
        <Link
          href="/patient/onboarding"
          className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-bold text-slate-950 hover:bg-cyan-400"
        >
          {patient ? "Update registration status" : "Get my Health ID"}
        </Link>
      </div>

      {reviews.length > 0 && (
        <Card title="Identity review status">
          <div className="space-y-2">
            {reviews.map((review) => (
              <div key={review.id} className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
                <p className="font-semibold">Duplicate review: {review.status}</p>
                <p className="mt-1">
                  Confidence {review.confidence.toFixed(2)} · submitted{" "}
                  {new Date(review.created_at).toLocaleString()}
                </p>
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
              <p className="mt-1 text-3xl font-bold tracking-wide text-slate-950">
                {patient.display_health_id}
              </p>
              <p className="mt-2 text-sm text-slate-700">
                {patient.given_name} {patient.family_name} · {patient.issuing_jurisdiction}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-600">
              You have not registered a Health ID yet. Use <strong>Get my Health ID</strong> above.
            </p>
          )}
          <div className="mt-5 flex gap-2">
            <Field value={healthId} onChange={(event) => setHealthId(event.target.value)} placeholder="Health ID"/>
            <button onClick={() => run(() => api.patient(healthId), setPatient)} className="rounded-lg bg-slate-900 px-4 text-sm font-semibold text-white">
              Lookup
            </button>
          </div>
        </Card>

        <Card title="Consent & emergency profile">
          <div className="flex flex-wrap gap-2">
            <button onClick={() => run(() => api.consents(healthId || patient?.display_health_id || ""), setConsents)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-50">
              View consent
            </button>
            <button onClick={() => run(() => api.emergency(healthId || patient?.display_health_id || ""), setEmergency)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold hover:bg-slate-50">
              Emergency profile
            </button>
          </div>
          {consents !== null && <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(consents, null, 2)}</pre>}
          {emergency !== null && <pre className="mt-4 max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(emergency, null, 2)}</pre>}
          {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        </Card>
      </div>
    </PortalShell>
  );
}
