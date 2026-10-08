"use client";

import { useEffect, useState } from "react";

import { api, type CurrentRecordLocation, type Provider, type Repository, type Transfer } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function AdminPortal() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [healthId, setHealthId] = useState("");
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [currentLocation, setCurrentLocation] = useState<CurrentRecordLocation | null>(null);
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [migrationMessage, setMigrationMessage] = useState("");

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [initialPassword, setInitialPassword] = useState("");
  const [givenName, setGivenName] = useState("");
  const [familyName, setFamilyName] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [jurisdiction, setJurisdiction] = useState("IN-OD");
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

  useEffect(() => {
    if (!transfer?.id || transfer.state === "COMPLETED") return;

    const refresh = async () => {
      try {
        const latest = await api.transferStatus(transfer.id);
        setTransfer(latest);
      } catch {
        // Keep the current state visible if a background refresh temporarily fails.
      }
    };

    const timer = window.setInterval(() => {
      void refresh();
    }, 2000);

    return () => window.clearInterval(timer);
  }, [transfer?.id, transfer?.state]);


  async function migrate() {
    setError("");
    setMigrationMessage("");
    try {
      const created = await api.createTransfer({
        health_id: healthId.trim(),
        source_repository_id: source,
        destination_repository_id: destination,
        purpose: "MIGRATION",
        scope: "FHIR",
      });
      setTransfer(created);
      setResult(created);
      setMigrationMessage("Migration request created. Patient authorization is required.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Migration request failed");
    }
  }

  async function loadCurrentLocation() {
    setError("");
    setCurrentLocation(null);
    if (!healthId.trim()) {
      setError("Enter a Patient Health ID first");
      return;
    }
    try {
      setCurrentLocation(await api.currentRecordLocation(healthId.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not find the patient's current repository");
    }
  }

  async function registerProvider() {
    setProviderMessage("");
    try {
      const result = await api.onboardProvider({username:username.trim(),email:email.trim(),initial_password:initialPassword,
        given_name:givenName.trim(),family_name:familyName.trim(),license_number:licenseNumber.trim(),jurisdiction:jurisdiction.trim()});
      setProviderMessage(`Doctor account created. Provider ID: ${result.provider.external_id}. Share the username and initial password with the doctor.`);
      setUsername(""); setEmail(""); setInitialPassword(""); setGivenName(""); setFamilyName(""); setLicenseNumber("");
      await loadProviders();
    } catch (e) { setProviderMessage(e instanceof Error ? e.message : "Doctor onboarding failed"); }
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
            Create the doctor account and HealthNet Provider ID together. HealthNet generates the Provider ID automatically; the doctor will see it after login and can share it with patients.
          </p>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Field value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Doctor username" />
            <Field type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Doctor email" />
            <Field type="password" value={initialPassword} onChange={(e) => setInitialPassword(e.target.value)} placeholder="Initial password (min 8 characters)" />
            <Field value={licenseNumber} onChange={(e) => setLicenseNumber(e.target.value)} placeholder="License number" />
            <Field value={givenName} onChange={(e) => setGivenName(e.target.value)} placeholder="Given name" />
            <Field value={familyName} onChange={(e) => setFamilyName(e.target.value)} placeholder="Family name" />
            <Field value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} placeholder="Jurisdiction (e.g. IN-OD)" />
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
            <p className="mt-2 text-xs font-medium text-slate-600">Provider IDs are generated by HealthNet. The doctor logs in with the account created here and sees the ID in the Doctor Portal.</p>
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

          <Card title="Patient record custody & migration">
            <p className="text-sm text-slate-700">
              Each patient has one authoritative repository. HealthNet does not scan other repositories when a doctor requests the record.
            </p>
            <div className="mt-3 flex gap-2">
              <Field value={healthId} onChange={(e) => setHealthId(e.target.value)} placeholder="Patient Health ID" />
              <button onClick={loadCurrentLocation} className="rounded-lg border-2 border-slate-400 px-4 py-2 text-sm font-bold text-slate-900">Find current repository</button>
            </div>
            {currentLocation && (
              <div className="mt-3 rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm">
                <p className="font-bold text-slate-950">Current: {currentLocation.repository_name}</p>
                <p className="text-slate-700">{currentLocation.repository_code} · {currentLocation.jurisdiction}</p>
              </div>
            )}
            <div className="mt-5 space-y-3">
              <select value={source} onChange={(e) => setSource(e.target.value)} className="w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-950">
                <option value="">Source repository</option>
                {repos.map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
              </select>
              <select value={destination} onChange={(e) => setDestination(e.target.value)} className="w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-950">
                <option value="">Destination repository</option>
                {repos.map((r) => <option key={r.id} value={r.id}>{r.code} — {r.name}</option>)}
              </select>
              <button onClick={migrate} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800">Request repository move</button>
              {transfer && (
                <div className="rounded-lg border border-cyan-300 bg-cyan-50 p-3 text-sm">
                  <p className="font-bold text-slate-950">Migration state: {transfer.state}</p>
                  {transfer.state === "PATIENT_AUTHORIZED" && (
                    <button
                      onClick={async () => {
                        try {
                          await api.issueTransferToken(transfer.id);
                          const completed = await api.executeTransfer(transfer.id, { resource_count: 8, package_hash: "DEMO-FHIR-PACKAGE-INTEGRITY-0001" });
                          const updatedLocation = await api.currentRecordLocation(healthId.trim());
                          setTransfer({ ...transfer, state: "COMPLETED", package_hash: "DEMO-FHIR-PACKAGE-INTEGRITY-0001" });
                          setCurrentLocation(updatedLocation);
                          setResult(completed);
                          setMigrationMessage(`Migration completed. The patient's active repository is now ${updatedLocation.repository_name} (${updatedLocation.repository_code}).`);
                        } catch (e) {
                          setMigrationMessage(e instanceof Error ? e.message : "Migration execution failed");
                        }
                      }}
                      className="mt-3 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-bold text-white"
                    >
                      Complete validated migration
                    </button>
                  )}
                  <p className="mt-2 text-slate-700">{migrationMessage}</p>
                </div>
              )}
              {result !== null && (
                <pre className="overflow-auto rounded-lg border-2 border-slate-300 bg-slate-100 p-3 text-xs font-medium text-slate-900">{JSON.stringify(result, null, 2)}</pre>
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
