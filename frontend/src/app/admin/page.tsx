"use client";

import { useEffect, useState } from "react";

import { api, type Provider, type Repository } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function AdminPortal() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [healthId, setHealthId] = useState("");
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");

  const [providerId, setProviderId] = useState("PRV-IN-000001");
  const [givenName, setGivenName] = useState("Test");
  const [familyName, setFamilyName] = useState("Doctor");
  const [licenseNumber, setLicenseNumber] = useState("TEST-DOC-001");
  const [jurisdiction, setJurisdiction] = useState("IN-OD");
  const [keycloakSubject, setKeycloakSubject] = useState("");
  const [providerMessage, setProviderMessage] = useState("");

  async function loadProviders() {
    try {
      setProviders(await api.providers());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load providers");
    }
  }

  useEffect(() => {
    api.repositories()
      .then(setRepos)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load repositories"));
    void loadProviders();
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

  async function registerProvider() {
    setProviderMessage("");
    try {
      await api.createProvider({
        external_id: providerId.trim(),
        given_name: givenName.trim(),
        family_name: familyName.trim(),
        license_number: licenseNumber.trim(),
        jurisdiction: jurisdiction.trim(),
        ...(keycloakSubject.trim() ? { keycloak_subject: keycloakSubject.trim() } : {}),
      });
      setProviderMessage(`Provider ${providerId.trim()} created successfully.`);
      setKeycloakSubject("");
      await loadProviders();
    } catch (e) {
      setProviderMessage(e instanceof Error ? e.message : "Provider registration failed");
    }
  }

  return (
    <PortalShell
      requiredRole="admin"
      title="Admin Portal"
      description="Repository registry, trusted provider mapping and controlled EHR migration coordination."
    >
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="HealthNet Provider Registry">
          <p className="text-sm text-slate-700">
            Link a Keycloak doctor account to a stable HealthNet Provider ID. Patients use the Provider ID for consent; the Keycloak subject remains internal.
          </p>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Field value={providerId} onChange={(e) => setProviderId(e.target.value)} placeholder="Provider ID (e.g. PRV-IN-000001)" />
            <Field value={licenseNumber} onChange={(e) => setLicenseNumber(e.target.value)} placeholder="License number" />
            <Field value={givenName} onChange={(e) => setGivenName(e.target.value)} placeholder="Given name" />
            <Field value={familyName} onChange={(e) => setFamilyName(e.target.value)} placeholder="Family name" />
            <Field value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} placeholder="Jurisdiction (e.g. IN-OD)" />
            <Field value={keycloakSubject} onChange={(e) => setKeycloakSubject(e.target.value)} placeholder="Doctor Keycloak subject" />
          </div>

          <button
            onClick={registerProvider}
            className="mt-3 rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800"
          >
            Register Provider
          </button>

          {providerMessage && (
            <p className="mt-3 rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm font-semibold text-slate-800">
              {providerMessage}
            </p>
          )}

          <div className="mt-5 space-y-2">
            <h3 className="font-bold text-slate-950">Registered providers</h3>
            {providers.length === 0 ? (
              <p className="text-sm text-slate-600">No providers registered yet.</p>
            ) : (
              providers.map((provider) => (
                <div key={provider.id} className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm">
                  <div className="flex flex-wrap justify-between gap-2">
                    <strong>{provider.external_id}</strong>
                    <span>{provider.trust_status}</span>
                  </div>
                  <p className="text-slate-700">
                    {provider.given_name} {provider.family_name} · {provider.jurisdiction}
                  </p>
                  <p className="break-all font-mono text-xs text-slate-600">
                    {provider.keycloak_subject || "Not linked"}
                  </p>
                </div>
              ))
            )}
          </div>
        </Card>

        <div className="space-y-5">
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
            </div>
          </Card>

          <Card title="Start EHR migration">
            <div className="space-y-3">
              <Field value={healthId} onChange={(e) => setHealthId(e.target.value)} placeholder="Patient Health ID" />
              <select value={source} onChange={(e) => setSource(e.target.value)} className="w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-950">
                <option value="">Source repository</option>
                {repos.map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
              </select>
              <select value={destination} onChange={(e) => setDestination(e.target.value)} className="w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-950">
                <option value="">Destination repository</option>
                {repos.map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
              </select>
              <button onClick={migrate} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800">
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
      </div>

      {error && (
        <p className="mt-5 rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-800">
          {error}
        </p>
      )}
    </PortalShell>
  );
}
