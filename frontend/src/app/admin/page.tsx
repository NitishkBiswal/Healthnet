"use client";

import { useEffect, useState } from "react";

import { api, type MedicalImportResult, type Provider, type Repository, type RepositorySummary, type Transfer } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

type AdminTab = "overview" | "repositories" | "integrations" | "transfers" | "providers" | "imports";

const tabs: { id: AdminTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "repositories", label: "Primary Repositories" },
  { id: "integrations", label: "Repository Integrations" },
  { id: "transfers", label: "Transfer Requests" },
  { id: "providers", label: "Provider Registry" },
  { id: "imports", label: "Medical Records Import" },
];

function stateLabel(state: string) {
  return state.replaceAll("_", " ");
}

export default function AdminPortal() {
  const [activeTab, setActiveTab] = useState<AdminTab>("overview");
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoSummaries, setRepoSummaries] = useState<RepositorySummary[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [adminTransfers, setAdminTransfers] = useState<Transfer[]>([]);
  const [error, setError] = useState("");
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
    catch (e) { setError(e instanceof Error ? e.message : "Could not load transfer requests"); }
  }

  async function loadProviders() {
    try { setProviders(await api.providers()); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load providers"); }
  }

  async function loadRepositories() {
    try {
      const [all, summaries] = await Promise.all([api.repositories(), api.repositorySummaries()]);
      setRepos(all);
      setRepoSummaries(summaries);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load repository information");
    }
  }

  async function refreshAll() {
    setError("");
    await Promise.all([loadRepositories(), loadAdminTransfers(), loadProviders()]);
  }

  useEffect(() => {
    void refreshAll();
  }, []);

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
      const manifest = completed as { resource_count?: number; validation_status?: string; package_hash?: string };
      setMigrationMessage(
        `Transfer for ${item.health_id} completed: ${manifest.resource_count ?? 0} FHIR resources imported; destination validation ${manifest.validation_status ?? "completed"}. Package SHA-256: ${manifest.package_hash ?? "not returned"}`
      );
      await Promise.all([loadAdminTransfers(), loadRepositories()]);
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
      const result = await api.onboardProvider({
        username: username.trim(), email: email.trim(), initial_password: initialPassword,
        given_name: givenName.trim(), family_name: familyName.trim(),
        license_number: licenseNumber.trim(), jurisdiction: jurisdiction.trim()
      });
      setProviderMessage(`Doctor account created. Provider ID: ${result.provider.external_id}. Share the username and initial password with the doctor.`);
      setUsername(""); setEmail(""); setInitialPassword(""); setGivenName(""); setFamilyName(""); setLicenseNumber("");
      await loadProviders();
    } catch (e) { setProviderMessage(e instanceof Error ? e.message : "Doctor onboarding failed"); }
  }

  function repositoryName(id: string) {
    return repos.find((repository) => repository.id === id)?.name ?? "Repository details unavailable";
  }

  // IN-KA and IN-OD are the two primary state repositories for the current
  // Karnataka–Odisha deployment. Other configured destinations are integrations.
  const primaryRepositories = repoSummaries.filter((repository) => ["IN-KA", "IN-OD"].includes(repository.code));
  const repositoryIntegrations = repoSummaries.filter((repository) => !["IN-KA", "IN-OD"].includes(repository.code));
  const activePatients = repoSummaries.reduce((total, repository) => total + repository.active_patient_count, 0);
  const pendingTransfers = adminTransfers.filter((item) => !["COMPLETED", "REJECTED", "FAILED"].includes(item.state)).length;
  const completedTransfers = adminTransfers.filter((item) => item.state === "COMPLETED").length;
  const reviewWaiting = adminTransfers.filter((item) => item.state === "PENDING_AUDITOR_REVIEW").length;

  return (
    <PortalShell
      requiredRole="admin"
      title="Admin Portal"
      description="Manage repositories, patient transfers, trusted providers and legacy medical-record imports."
    >
      <div className="mb-5 flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-sm">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-lg px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-slate-950 text-white shadow" : "text-slate-700 hover:bg-slate-100"}`}
          >
            {tab.label}
            {tab.id === "transfers" && pendingTransfers > 0 && (
              <span className={`ml-2 rounded-full px-2 py-0.5 text-xs ${activeTab === tab.id ? "bg-white/20 text-white" : "bg-amber-100 text-amber-900"}`}>{pendingTransfers}</span>
            )}
          </button>
        ))}
        <button type="button" onClick={() => void refreshAll()} className="ml-auto rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">Refresh data</button>
      </div>

      {activeTab === "overview" && (
        <div className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Registered repositories", value: repos.length, detail: "Configured HealthNet destinations" },
              { label: "Patients in active custody", value: activePatients, detail: "Unique active patient assignments" },
              { label: "Transfers requiring action", value: pendingTransfers, detail: `${reviewWaiting} waiting for Auditor review` },
              { label: "Completed transfers", value: completedTransfers, detail: "Verified repository moves" },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-semibold text-slate-600">{item.label}</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-slate-950">{item.value}</p>
                <p className="mt-1 text-xs text-slate-500">{item.detail}</p>
              </div>
            ))}
          </div>
          <Card title="Primary repository distribution">
            <p className="mb-4 text-sm text-slate-600">The current deployment's two primary state repositories. Patient assignments are counted from the active HealthNet record locator.</p>
            <div className="grid gap-3 md:grid-cols-2">
              {primaryRepositories.map((repository) => (
                <div key={repository.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div><p className="font-bold text-slate-950">{repository.name}</p><p className="mt-1 text-xs text-slate-600">{repository.code} · {repository.jurisdiction}</p></div>
                    <span className={`rounded-full px-2 py-1 text-xs font-bold ${repository.status === "ONLINE" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>{repository.status}</span>
                  </div>
                  <p className="mt-4 text-3xl font-bold tabular-nums text-slate-950">{repository.active_patient_count}</p>
                  <p className="text-xs font-medium text-slate-600">Patients currently assigned</p>
                </div>
              ))}
              {primaryRepositories.length === 0 && <p className="text-sm text-slate-600">No primary repositories are configured.</p>}
            </div>
          </Card>
          <Card title="Additional repository integrations">
            <p className="mb-3 text-sm text-slate-600">These are separately configured destinations or integration endpoints. They are retained for compatibility and future expansion; they are not counted as primary state repositories.</p>
            {repositoryIntegrations.length === 0 ? <p className="text-sm text-slate-600">No additional integrations are configured.</p> : (
              <div className="space-y-2">
                {repositoryIntegrations.map((repository) => (
                  <div key={repository.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-3">
                    <div><p className="font-semibold text-slate-950">{repository.name}</p><p className="text-xs text-slate-600">{repository.code} · {repository.jurisdiction}</p></div>
                    <div className="text-right"><span className={`rounded-full px-2 py-1 text-xs font-bold ${repository.status === "ONLINE" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>{repository.status}</span><p className="mt-1 text-xs text-slate-500">{repository.active_patient_count} active patients</p></div>
                  </div>
                ))}
              </div>
            )}
          </Card>
          <Card title="Latest transfer activity">
            {adminTransfers.length === 0 ? <p className="text-sm text-slate-600">No repository transfer requests found.</p> : (
              <div className="space-y-2">
                {adminTransfers.slice(0, 5).map((item) => (
                  <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 p-3 text-sm">
                    <div><p className="font-bold text-slate-950">{item.health_id}</p><p className="text-xs text-slate-600">{repositoryName(item.source_repository_id)} → {repositoryName(item.destination_repository_id)}</p></div>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">{stateLabel(item.state)}</span>
                  </div>
                ))}
                <button type="button" onClick={() => setActiveTab("transfers")} className="text-sm font-bold text-cyan-800 underline">View all transfer requests</button>
              </div>
            )}
          </Card>
        </div>
      )}

      {activeTab === "repositories" && (
        <Card title="Primary repository registry">
          <p className="mb-4 text-sm text-slate-600">Primary repositories for the current Karnataka–Odisha deployment. Patient counts are based on active HealthNet record-locator assignments.</p>
          {primaryRepositories.length === 0 ? <p className="text-sm text-slate-600">No primary repositories are configured.</p> : (
            <div className="space-y-3">
              {primaryRepositories.map((repository) => (
                <div key={repository.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><h3 className="font-bold text-slate-950">{repository.name}</h3><p className="mt-1 text-xs text-slate-600">{repository.code} · {repository.jurisdiction}</p></div>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800">{repository.status}</span>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Active patients</p><p className="text-2xl font-bold tabular-nums text-slate-950">{repository.active_patient_count}</p></div>
                    <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Jurisdiction</p><p className="mt-1 font-bold text-slate-900">{repository.jurisdiction}</p></div>
                  </div>
                  <p className="mt-3 break-all text-xs text-slate-600">FHIR endpoint: {repository.base_url}</p>
                  {repository.description && <p className="mt-1 text-sm text-slate-600">{repository.description}</p>}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {activeTab === "integrations" && (
        <Card title="Additional repository integrations">
          <p className="mb-4 text-sm text-slate-600">These configured destinations are kept separate from the primary state repositories. Their presence in this list does not by itself confirm that their FHIR endpoint is reachable; use the configured status and endpoint details for operational verification.</p>
          {repositoryIntegrations.length === 0 ? <p className="text-sm text-slate-600">No additional integrations are configured.</p> : (
            <div className="space-y-3">
              {repositoryIntegrations.map((repository) => (
                <div key={repository.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><h3 className="font-bold text-slate-950">{repository.name}</h3><p className="mt-1 text-xs text-slate-600">{repository.code} · {repository.jurisdiction}</p></div>
                    <span className={`rounded-full px-3 py-1 text-xs font-bold ${repository.status === "ONLINE" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>{repository.status}</span>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Active patients</p><p className="text-2xl font-bold tabular-nums text-slate-950">{repository.active_patient_count}</p></div>
                    <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Jurisdiction</p><p className="mt-1 font-bold text-slate-900">{repository.jurisdiction}</p></div>
                  </div>
                  <p className="mt-3 break-all text-xs text-slate-600">Configured FHIR endpoint: {repository.base_url}</p>
                  {repository.description && <p className="mt-1 text-sm text-slate-600">{repository.description}</p>}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {activeTab === "transfers" && (
        <Card title="Patient-initiated repository transfer requests">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <p className="max-w-3xl text-sm text-slate-600">This is the complete transfer register, including pending, rejected, failed and completed requests. The patient authorizes the move; the Auditor independently approves requests that trigger review; Admin executes only eligible transfers.</p>
            <button type="button" onClick={() => void loadAdminTransfers()} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700">Refresh requests</button>
          </div>
          {adminTransfers.length === 0 ? <p className="text-sm text-slate-600">No transfer requests have been submitted.</p> : (
            <div className="space-y-3">
              {adminTransfers.map((item) => {
                const canExecute = item.state === "PATIENT_AUTHORIZED" || item.state === "TRANSFER_AUTH_ISSUED";
                return (
                  <div key={item.id} className="rounded-xl border border-slate-200 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div><p className="font-bold text-slate-950">Health ID: {item.health_id}</p><p className="mt-1 text-sm text-slate-700">{repositoryName(item.source_repository_id)} → {repositoryName(item.destination_repository_id)}</p></div>
                      <span className={`rounded-full px-3 py-1 text-xs font-bold ${item.state === "COMPLETED" ? "bg-emerald-100 text-emerald-800" : item.state === "PENDING_AUDITOR_REVIEW" ? "bg-amber-100 text-amber-900" : item.state === "REJECTED" || item.state === "FAILED" ? "bg-red-100 text-red-800" : "bg-slate-100 text-slate-800"}`}>{stateLabel(item.state)}</span>
                    </div>
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs font-semibold text-slate-500">Patient's reason</p><p className="mt-1 text-sm text-slate-900">{item.reason}</p></div>
                      <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs font-semibold text-slate-500">Approval status</p><p className="mt-1 text-sm font-bold text-slate-900">{item.review_required ? `Auditor review: ${item.review_status}` : "Auditor review not required"}</p>{item.reviewed_at && <p className="mt-1 text-xs text-slate-600">Reviewed {new Date(item.reviewed_at).toLocaleString()}</p>}{item.reviewer_note && <p className="mt-1 text-xs text-slate-600">Note: {item.reviewer_note}</p>}</div>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs text-slate-500">Submitted {new Date(item.created_at).toLocaleString()} · ID {item.id}</p>
                      {canExecute && <button type="button" onClick={() => void completeQueuedTransfer(item)} className="rounded-lg bg-emerald-700 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-800">Execute verified transfer</button>}
                    </div>
                    {item.state === "PENDING_AUDITOR_REVIEW" && <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs font-semibold text-amber-900">Waiting for independent Auditor approval. Transfer execution is disabled.</p>}
                    {item.state === "REQUESTED" && <p className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-700">Waiting for patient authorization.</p>}
                    {item.error_message && <p className="mt-2 text-xs text-red-700">{item.error_message}</p>}
                    {item.package_hash && <p className="mt-2 break-all text-xs text-slate-500">Verified package SHA-256: {item.package_hash}</p>}
                  </div>
                );
              })}
            </div>
          )}
          {migrationMessage && <p className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-900">{migrationMessage}</p>}
        </Card>
      )}

      {activeTab === "providers" && (
        <div className="grid gap-5 lg:grid-cols-2">
          <Card title="Register a healthcare provider">
            <p className="text-sm text-slate-700">Create the doctor account and HealthNet Provider ID together. HealthNet generates the Provider ID automatically; the doctor will see it after login.</p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <Field value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Doctor username" />
              <Field type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Doctor email" />
              <Field type="password" value={initialPassword} onChange={(e) => setInitialPassword(e.target.value)} placeholder="Initial password (min 8 characters)" />
              <Field value={licenseNumber} onChange={(e) => setLicenseNumber(e.target.value)} placeholder="License number" />
              <Field value={givenName} onChange={(e) => setGivenName(e.target.value)} placeholder="Given name" />
              <Field value={familyName} onChange={(e) => setFamilyName(e.target.value)} placeholder="Family name" />
              <Field value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} placeholder="Jurisdiction (e.g. IN-OD)" />
            </div>
            <button onClick={registerProvider} className="mt-3 rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800">Register Provider</button>
            {providerMessage && <p className="mt-3 rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm font-semibold text-slate-800">{providerMessage}</p>}
          </Card>
          <Card title="Registered providers">
            <p className="mb-3 text-xs text-slate-600">Provider IDs are generated by HealthNet and linked to the provider's login account.</p>
            {providers.length === 0 ? <p className="text-sm text-slate-600">No providers registered yet.</p> : (
              <div className="space-y-2">{providers.map((provider) => (
                <div key={provider.id} className="rounded-lg border border-slate-300 bg-slate-50 p-3 text-sm">
                  <div className="flex flex-wrap justify-between gap-2"><strong>{provider.external_id}</strong><span>{provider.trust_status}</span></div>
                  <p className="text-slate-700">{provider.given_name} {provider.family_name} · {provider.jurisdiction}</p>
                  <p className="break-all font-mono text-xs text-slate-600">{provider.keycloak_subject || "Not linked"}</p>
                </div>
              ))}</div>
            )}
          </Card>
        </div>
      )}

      {activeTab === "imports" && (
        <Card title="Import existing medical records (CSV / Excel)">
          <p className="text-sm text-slate-700">Admin-only import. Each row is matched to a HealthNet Health ID and routed to that patient's active repository. Supported record types: CONDITION and OBSERVATION.</p>
          <div className="mt-3 rounded-lg border border-slate-300 bg-slate-50 p-3 text-xs text-slate-700">
            Required columns: <strong>health_id, record_type, record_id, display, recorded_at</strong>. Optional: code, code_system, status, value, unit, source_hospital, is_chronic, emergency_relevant. Dates must use ISO format (YYYY-MM-DD or ISO datetime). Max 5,000 rows / 10 MB.
            <p className="mt-2">Only mark a condition for the emergency summary when both is_chronic and emergency_relevant are TRUE. Do not upload real patient data to an unsecured demo environment.</p>
            <div className="mt-3 flex flex-wrap gap-4">
              <a className="inline-block font-semibold underline" href="/medical-record-import-template.csv" download>Download blank/example CSV template</a>
              <a className="inline-block font-semibold underline" href="/demo-medical-records.csv" download>Download seeded demo patient records</a>
            </div>
            <p className="mt-2 text-xs text-slate-500">The seeded demo file is generated by backend/scripts/seed_demo_patients.py and contains Health IDs for testpatient1–testpatient4. Run the local demo seeding script first.</p>
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
      )}

      {error && <p className="mt-5 rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-800">{error}</p>}
    </PortalShell>
  );
}
