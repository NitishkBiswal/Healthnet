"use client";

import { useState } from "react";
import Link from "next/link";

import { api, type RegistrationResult } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function PatientOnboardingPage() {
  const [form, setForm] = useState({
    given_name: "",
    family_name: "",
    date_of_birth: "",
    sex: "",
    phone: "",
    email: "",
    address: "",
    issuing_jurisdiction: "IN-OD",
  });
  const [result, setResult] = useState<RegistrationResult | null>(null);
  const [error, setError] = useState("");

  function update(name: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function submit() {
    setError("");
    setResult(null);
    try {
      const response = await api.registerPatient({
        ...form,
        sex: form.sex || undefined,
        phone: form.phone || undefined,
        email: form.email || undefined,
        address: form.address || undefined,
      });
      setResult(response);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Registration failed");
    }
  }

  return (
    <PortalShell
      requiredRole="patient"
      title="Get your Health ID"
      description="Register your identity once. Your Health ID remains permanent even when you move between jurisdictions."
    >
      <Card title="First-time patient registration">
        <div className="grid gap-4 md:grid-cols-2">
          <Field placeholder="Given name" value={form.given_name} onChange={(e) => update("given_name", e.target.value)} />
          <Field placeholder="Family name" value={form.family_name} onChange={(e) => update("family_name", e.target.value)} />
          <Field type="date" value={form.date_of_birth} onChange={(e) => update("date_of_birth", e.target.value)} />
          <Field placeholder="Sex (optional)" value={form.sex} onChange={(e) => update("sex", e.target.value)} />
          <Field placeholder="Phone (optional)" value={form.phone} onChange={(e) => update("phone", e.target.value)} />
          <Field type="email" placeholder="Email (optional)" value={form.email} onChange={(e) => update("email", e.target.value)} />
          <Field placeholder="Address (optional)" value={form.address} onChange={(e) => update("address", e.target.value)} />
          <select value={form.issuing_jurisdiction} onChange={(e) => update("issuing_jurisdiction", e.target.value)} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
            <option value="IN-OD">India — Odisha</option>
            <option value="IN-KA">India — Karnataka</option>
            <option value="MV">Maldives</option>
          </select>
        </div>
        <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
          HealthNet checks for an existing identity before issuing a new Health ID. Ambiguous matches go to an Auditor instead of creating a second identity.
        </div>
        {error && <p className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {result && (
          <div className="mt-5 rounded-xl border border-cyan-200 bg-cyan-50 p-5">
            <p className="font-semibold text-slate-950">{result.outcome.replaceAll("_", " ")}</p>
            {result.patient && <p className="mt-2 text-2xl font-bold tracking-wide text-slate-950">{result.patient.display_health_id}</p>}
            {result.matches.length > 0 && (
              <div className="mt-3 text-sm text-slate-700">
                <p className="font-semibold">Possible existing identity</p>
                {result.matches.map((match) => <p key={match.patient_id}>{match.health_id} · {match.band} confidence ({match.confidence.toFixed(2)})</p>)}
              </div>
            )}
            {result.duplicate_review_id && <p className="mt-3 text-sm font-semibold text-amber-800">Your registration has been sent to an Auditor for duplicate review.</p>}
          </div>
        )}
        <div className="mt-6 flex gap-3">
          <button onClick={submit} className="rounded-lg bg-cyan-500 px-5 py-2.5 text-sm font-bold text-slate-950 hover:bg-cyan-400">Check & get Health ID</button>
          <Link href="/patient" className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold hover:bg-slate-50">Back to Patient Portal</Link>
        </div>
      </Card>
    </PortalShell>
  );
}
