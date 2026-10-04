"use client";
import { useEffect, useState } from "react";
import { api, type Repository } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function AdminPortal() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [healthId, setHealthId] = useState("");
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.repositories()
      .then(setRepos)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load repositories"));
  }, []);

  async function migrate() {
    setError("");
    try {
      setResult(await api.createTransfer({
        health_id: healthId,
        source_repository_id: source,
        destination_repository_id: destination,
        purpose: "MIGRATION",
        scope: "FHIR",
      }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Migration request failed");
    }
  }

  return (
    <PortalShell
      requiredRole="admin"
      title="Admin Portal"
      description="Repository registry and controlled EHR migration coordination."
    >
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Jurisdictional repositories">
          <div className="space-y-3">
            {repos.map((r) => (
              <div key={r.id} className="rounded-lg border-2 border-slate-300 bg-slate-50 p-3">
                <div className="flex justify-between gap-3">
                  <strong className="text-slate-950">{r.name}</strong>
                  <span className="text-xs font-bold text-emerald-800">{r.status}</span>
                </div>
                <p className="text-xs font-medium text-slate-700">
                  {r.code} · {r.jurisdiction} · {r.base_url}
                </p>
              </div>
            ))}
            {error && (
              <p className="rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-800">
                {error}
              </p>
            )}
          </div>
        </Card>

        <Card title="Start EHR migration">
          <div className="space-y-3">
            <Field
              value={healthId}
              onChange={(e) => setHealthId(e.target.value)}
              placeholder="Patient Health ID"
            />
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-950 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-300"
            >
              <option value="">Source repository</option>
              {repos.map((r) => (
                <option key={r.id} value={r.id}>{r.code} — {r.name}</option>
              ))}
            </select>
            <select
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-950 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-300"
            >
              <option value="">Destination repository</option>
              {repos.map((r) => (
                <option key={r.id} value={r.id}>{r.code} — {r.name}</option>
              ))}
            </select>
            <button
              onClick={migrate}
              className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white shadow-sm hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              Create migration request
            </button>
            {result !== null && (
              <pre className="overflow-auto rounded-lg border-2 border-slate-300 bg-slate-100 p-3 text-xs font-medium text-slate-900">
                {JSON.stringify(result, null, 2)}
              </pre>
            )}
          </div>
        </Card>
      </div>
    </PortalShell>
  );
}
