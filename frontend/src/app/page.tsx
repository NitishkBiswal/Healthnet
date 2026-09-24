"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  decideDuplicateReview,
  fetchDuplicateReviews,
  fetchHealth,
  fetchPatient,
  registerPatient,
  type Patient,
  type RegistrationRequest,
  type RegistrationResult,
} from "@/lib/api";

function Badge({ children, tone = "slate" }: { children: React.ReactNode; tone?: "green" | "yellow" | "red" | "slate" }) {
  const styles = {
    green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    yellow: "bg-amber-50 text-amber-700 ring-amber-600/20",
    red: "bg-red-50 text-red-700 ring-red-600/20",
    slate: "bg-slate-100 text-slate-700 ring-slate-600/20",
  };
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${styles[tone]}`}>{children}</span>;
}

function PatientCard({ patient }: { patient: Patient }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Permanent Health ID</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">{patient.display_health_id}</p>
        </div>
        <Badge tone={patient.status === "ACTIVE" ? "green" : "yellow"}>{patient.status}</Badge>
      </div>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div><p className="text-xs text-slate-500">Patient</p><p className="font-medium text-slate-900">{patient.given_name} {patient.family_name}</p></div>
        <div><p className="text-xs text-slate-500">Date of birth</p><p className="font-medium text-slate-900">{patient.date_of_birth}</p></div>
        <div><p className="text-xs text-slate-500">Jurisdiction</p><p className="font-medium text-slate-900">{patient.issuing_jurisdiction}</p></div>
        <div><p className="text-xs text-slate-500">Created</p><p className="font-medium text-slate-900">{new Date(patient.created_at).toLocaleString()}</p></div>
      </div>
    </div>
  );
}

export default function Home() {
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth, refetchInterval: 15000 });
  const reviews = useQuery({ queryKey: ["duplicate-reviews"], queryFn: fetchDuplicateReviews });

  const [lookupId, setLookupId] = useState("");
  const [lookup, setLookup] = useState<Patient | null>(null);
  const [lookupError, setLookupError] = useState("");
  const [result, setResult] = useState<RegistrationResult | null>(null);
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<RegistrationRequest>({
    given_name: "",
    family_name: "",
    date_of_birth: "",
    sex: "",
    phone: "",
    email: "",
    address: "",
    issuing_jurisdiction: "IN-OD",
    identifiers: [],
  });

  function updateField(field: keyof RegistrationRequest, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleRegister(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    try {
      const response = await registerPatient(form);
      setResult(response);
      setMessage(response.outcome === "REGISTERED" ? "Patient registered and Health ID created." : `Registration returned: ${response.outcome}`);
      await reviews.refetch();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLookup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLookupError("");
    setLookup(null);
    try {
      setLookup(await fetchPatient(lookupId.trim()));
    } catch (error) {
      setLookupError(error instanceof Error ? error.message : "Patient not found");
    }
  }

  async function handleDecision(reviewId: string, decision: "APPROVED_DUPLICATE" | "REJECTED") {
    try {
      await decideDuplicateReview(reviewId, decision);
      await queryClient.invalidateQueries({ queryKey: ["duplicate-reviews"] });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not update review");
    }
  }

  const serviceHealthy = health.data?.status === "healthy";

  return (
    <main className="min-h-screen bg-slate-50 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-xl font-bold tracking-tight">HealthNet</p>
            <p className="text-xs text-slate-500">Global Health Identity Federation · Segment 1 Demo</p>
          </div>
          <Badge tone={serviceHealthy ? "green" : "red"}>{health.isLoading ? "Checking API" : serviceHealthy ? "API Healthy" : "API Offline"}</Badge>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-8 px-6 py-8">
        {message && <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">{message}</div>}

        <section className="grid gap-4 md:grid-cols-4">
          {[
            ["Identity", "Permanent Health IDs"],
            ["Matching", "Duplicate detection"],
            ["Review", "Human adjudication"],
            ["Movement", "Location history"],
          ].map(([title, subtitle]) => (
            <div key={title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-semibold">{title}</p>
              <p className="mt-1 text-xs text-slate-500">{subtitle}</p>
            </div>
          ))}
        </section>

        <section className="grid gap-8 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5">
              <h2 className="text-lg font-semibold">Register patient</h2>
              <p className="text-sm text-slate-500">Calls the real Segment 1 registration API.</p>
            </div>
            <form onSubmit={handleRegister} className="grid gap-4 sm:grid-cols-2">
              {[
                ["given_name", "Given name", "text"],
                ["family_name", "Family name", "text"],
                ["date_of_birth", "Date of birth", "date"],
                ["sex", "Sex", "text"],
                ["phone", "Phone", "tel"],
                ["email", "Email", "email"],
              ].map(([field, label, type]) => (
                <label key={field} className="grid gap-1.5 text-sm">
                  <span className="font-medium">{label}</span>
                  <input required={field === "given_name" || field === "family_name" || field === "date_of_birth"} type={type} value={String(form[field as keyof RegistrationRequest] ?? "")} onChange={(e) => updateField(field as keyof RegistrationRequest, e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-slate-500" />
                </label>
              ))}
              <label className="grid gap-1.5 text-sm sm:col-span-2">
                <span className="font-medium">Issuing jurisdiction</span>
                <input required value={form.issuing_jurisdiction} onChange={(e) => updateField("issuing_jurisdiction", e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <label className="grid gap-1.5 text-sm sm:col-span-2">
                <span className="font-medium">Address</span>
                <input value={form.address} onChange={(e) => updateField("address", e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2" />
              </label>
              <button disabled={submitting} className="rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50 sm:col-span-2">{submitting ? "Registering..." : "Register & generate Health ID"}</button>
            </form>
          </div>

          <div className="space-y-6">
            {result?.patient && <PatientCard patient={result.patient} />}
            {result && !result.patient && result.matches.length > 0 && (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
                <h3 className="font-semibold">Possible duplicate detected</h3>
                <p className="mt-1 text-sm text-amber-800">Outcome: {result.outcome}</p>
                <div className="mt-4 space-y-2">
                  {result.matches.map((match) => <div key={match.patient_id} className="rounded-lg bg-white p-3 text-sm"><b>{match.health_id}</b> · {(match.confidence * 100).toFixed(1)}% · {match.band}</div>)}
                </div>
              </div>
            )}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold">Find by Health ID</h2>
              <form onSubmit={handleLookup} className="mt-4 flex gap-2">
                <input required placeholder="e.g. INOD000001" value={lookupId} onChange={(e) => setLookupId(e.target.value)} className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2" />
                <button className="rounded-lg bg-slate-800 px-4 py-2 font-medium text-white">Find</button>
              </form>
              {lookupError && <p className="mt-3 text-sm text-red-600">{lookupError}</p>}
              {lookup && <div className="mt-4"><PatientCard patient={lookup} /></div>}
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div><h2 className="text-lg font-semibold">Duplicate review queue</h2><p className="text-sm text-slate-500">Human review of medium-confidence identity matches.</p></div>
            <button onClick={() => reviews.refetch()} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium">Refresh</button>
          </div>
          <div className="mt-5 space-y-3">
            {reviews.isLoading && <p className="text-sm text-slate-500">Loading reviews...</p>}
            {!reviews.isLoading && reviews.data?.length === 0 && <p className="text-sm text-slate-500">No duplicate reviews.</p>}
            {reviews.data?.map((review) => (
              <div key={review.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 p-4">
                <div className="text-sm">
                  <p className="font-medium">Review {review.id.slice(0, 8)}…</p>
                  <p className="text-slate-500">Candidate: {review.candidate_patient_id.slice(0, 8)}… · Confidence: {(review.confidence * 100).toFixed(1)}%</p>
                  <Badge tone={review.status === "PENDING" ? "yellow" : "slate"}>{review.status}</Badge>
                </div>
                {review.status === "PENDING" && <div className="flex gap-2"><button onClick={() => handleDecision(review.id, "APPROVED_DUPLICATE")} className="rounded-lg border border-red-200 px-3 py-2 text-sm text-red-700">Approve duplicate</button><button onClick={() => handleDecision(review.id, "REJECTED")} className="rounded-lg border border-emerald-200 px-3 py-2 text-sm text-emerald-700">Reject</button></div>}
              </div>
            ))}
          </div>
        </section>

        <footer className="pb-6 text-center text-xs text-slate-400">Development dashboard · uses live Segment 1 APIs · not the final Segment 13 UI</footer>
      </div>
    </main>
  );
}
