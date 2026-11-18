"use client";

import { useEffect, useState } from "react";

import { api, type CurrentRecordLocation, type MedicalImportResult, type Provider, type Repository, type Transfer } from "@/lib/api";
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
  const [transferReason, setTransferReason] = useState("");
  const [adminTransfers, setAdminTransfers] = useState<Transfer[]>([]);
  const [migrationMessage, setMigrationMessage] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<MedicalImportResult | null>(null);
  const [importBusy, setImportBusy] = useState(false);

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [initialPassword, setInitialPassword] = useState("");
  const [givenName, setGivenName] = useState("");
  const [familyName, setFamilyName] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [jurisdiction, setJurisdiction] = useState("IN-OD");
  const [providerMessage, setProviderMessage] = useState("");

  async function loadAdminTransfers() {
    try { setAdminTransfers(await api.adminTransfers()); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load transfer queue"); }
  }

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
    void loadAdminTransfers();
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
        reason: transferReason.trim(),
      });
      setTransfer(created);
      await loadAdminTransfers();
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

  async function completeQueuedTransfer(item: Transfer) {
    setError("");
    setMigrationMessage("");
    try {
      const authorization = await api.issueTransferToken(item.id);
      const completed = await api.executeTransfer(item.id, {
        authorization_token: authorization.authorization_token,
        resource_count: 0,
      });
      const latest = await api.transferStatus(item.id);
      setAdminTransfers((items) => items.map((value) => value.id === latest.id ? latest : value));
      if (healthId.trim() === item.health_id) {
        setCurrentLocation(await api.currentRecordLocation(item.health_id));
      }
      setMigrationMessage(`Transfer for ${item.health_id} completed. Destination records were verified before custody changed.`);
      setResult(completed);
      await loadAdminTransfers();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Transfer execution failed");
      await loadAdminTransfers();
    }
  }

  async function importRecords() {
    if (!importFile) { setError("Choose a CSV or Excel file first"); return; }
    setError(""); setImportResult(null); setImportBusy(true);
    try { setImportResult(await api.importMedicalRecords(importFile)); }
    catch (e) { setError(e instanceof Error ? e.message : "Medical record import failed"); }
    finally { setImportBusy(false); }
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
              <label className="block text-sm font-semibold text-slate-800">Reason for transfer
                <textarea value={transferReason} onChange={(e) => setTransferReason(e.target.value)} rows={2} minLength={10} placeholder="Explain why this patient record needs to move to the destination repository." className="mt-1 w-full rounded-lg border-2 border-slate-300 px-3 py-2 font-normal" />
              </label>
              <button disabled={transferReason.trim().length < 10} onClick={migrate} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-50">Request repository move</button>
              {transfer && (
                <div className="rounded-lg border border-cyan-300 bg-cyan-50 p-3 text-sm">
                  <p className="font-bold text-slate-950">Migration state: {transfer.state}</p>
                  {(transfer.state === "PATIENT_AUTHORIZED" || transfer.state === "TRANSFER_AUTH_ISSUED") && (
                    <button
                      onClick={async () => {
                        try {
                          const authorization = await api.issueTransferToken(transfer.id);
                          const completed = await api.executeTransfer(transfer.id, {
                            authorization_token: authorization.authorization_token,
                            resource_count: 0,
                          });
                          const updatedLocation = await api.currentRecordLocation(healthId.trim());
                          const latestTransfer = await api.transferStatus(transfer.id);
                          setTransfer(latestTransfer);
                          setCurrentLocation(updatedLocation);
                          setResult(completed);
                          const validation = typeof completed === "object" && completed !== null && "validation_status" in completed
                            ? String((completed as { validation_status: unknown }).validation_status)
                            : "VERIFIED";
                          setMigrationMessage(`Migration completed (${validation}). The patient's active repository is now ${updatedLocation.repository_name} (${updatedLocation.repository_code}).`);
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

      <div className="mt-5">
        <Card title="Patient-initiated repository transfer queue">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-slate-600">Transfers authorized by patients appear here. If Auditor review was triggered, the transfer cannot be executed until it is approved.</p>
            <button type="button" onClick={() => void loadAdminTransfers()} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700">Refresh queue</button>
          </div>
          {adminTransfers.length === 0 ? <p className="text-sm text-slate-600">No pending repository transfers.</p> : (
            <div className="space-y-3">
              {adminTransfers.map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-200 p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-bold text-slate-950">{item.health_id}</p>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-800">{item.state.replaceAll("_", " ")}</span>
                  </div>
                  <p className="mt-1 text-slate-700">Reason: {item.reason}</p>
                  {item.review_required && <p className="mt-1 font-semibold text-amber-800">Auditor review: {item.review_status}</p>}
                  {item.state === "PENDING_AUDITOR_REVIEW" && <p className="mt-2 text-amber-800">Waiting for Auditor approval.</p>}
                  {item.state === "PATIENT_AUTHORIZED" || item.state === "TRANSFER_AUTH_ISSUED" ? (
                    <button type="button" onClick={() => void completeQueuedTransfer(item)} className="mt-3 rounded-lg bg-emerald-700 px-4 py-2 text-xs font-bold text-white">Run verified transfer</button>
                  ) : null}
                  {item.error_message && <p className="mt-2 text-red-700">{item.error_message}</p>}
                </div>
              ))}
            </div>
          )}
          {migrationMessage && <p className="mt-3 text-sm font-semibold text-slate-700">{migrationMessage}</p>}
        </Card>
        <Card title="Import existing medical records (CSV / Excel)">
          <p className="text-sm text-slate-700">Admin-only import. Each row is matched to a HealthNet Health ID and routed to that patient's active repository. Supported record types: CONDITION and OBSERVATION.</p>
          <div className="mt-3 rounded-lg border border-slate-300 bg-slate-50 p-3 text-xs text-slate-700">
            Required columns: <strong>health_id, record_type, record_id, display, recorded_at</strong>. Optional: code, code_system, status, value, unit, source_hospital, is_chronic, emergency_relevant. Dates must use ISO format (YYYY-MM-DD or ISO datetime). Max 5,000 rows / 10 MB.
            <p className="mt-2">Only mark a condition for the emergency summary when both is_chronic and emergency_relevant are TRUE. Do not upload real patient data to an unsecured demo environment.</p>
            <a className="mt-2 inline-block font-semibold underline" href="/medical-record-import-template.csv" download>Download CSV template</a>
          </div>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
            <input type="file" accept=".csv,.xlsx,.xlsm" onChange={(event) => { setImportFile(event.target.files?.[0] ?? null); setImportResult(null); }} className="block w-full text-sm text-slate-800" />
            <button disabled={!importFile || importBusy} onClick={importRecords} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{importBusy ? "Importing..." : "Import valid rows"}</button>
          </div>
          {importResult && (
            <div className="mt-4 rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm">
              <p className="font-bold">Import finished</p>
              <p>Accepted: {importResult.accepted} · Failed: {importResult.failed} · Emergency summary additions: {importResult.emergency_conditions_added} · Patients: {importResult.patients_affected}</p>
              <p className="mt-1 break-all text-xs text-slate-600">File SHA-256: {importResult.file_sha256}</p>
              {importResult.errors.length > 0 && <div className="mt-3 max-h-56 overflow-auto"><p className="font-semibold">Rows requiring correction</p>{importResult.errors.map((item) => <p key={item.row} className="mt-1 text-xs">Row {item.row} ({item.health_id ?? "no Health ID"}): {item.error}</p>)}</div>}
            </div>
          )}
        </Card>
      </div>

      {error && (
        <p className="mt-5 rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-800">
          {error}
        </p>
      )}
    </PortalShell>
  );
}
