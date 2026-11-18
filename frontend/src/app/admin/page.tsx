"use client";

import { useEffect, useState } from "react";

import {
  api,
  type Jurisdiction,
  type PolicyRule,
  type Provider,
  type Repository,
  type Transfer,
} from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";

export default function AdminPortal() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repoOffset, setRepoOffset] = useState(0);
  const [hasMoreRepos, setHasMoreRepos] = useState(false);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [policyRules, setPolicyRules] = useState<PolicyRule[]>([]);
  const [policyForm, setPolicyForm] = useState({
    jurisdiction_code: "IN-OD", name: "", purpose: "TREATMENT", scope: "clinical",
    effect: "ALLOW" as "ALLOW" | "DENY", description: "",
  });
  const [ledgerIntegrity, setLedgerIntegrity] = useState<{ valid: boolean; entries_checked: number } | null>(null);
  const [transfer, setTransfer] = useState<Transfer | null>(null);
  const [transferLookupId, setTransferLookupId] = useState("");
  const [transferToken, setTransferToken] = useState("");
  const [transferBusy, setTransferBusy] = useState(false);
  const [transferMessage, setTransferMessage] = useState("");
  const [healthId, setHealthId] = useState("");
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [error, setError] = useState("");
  const [changeHealthId, setChangeHealthId] = useState("");
  const [changeRepositoryId, setChangeRepositoryId] = useState("");
  const [changeBusy, setChangeBusy] = useState(false);
  const [repositoryMessage, setRepositoryMessage] = useState("");

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [initialPassword, setInitialPassword] = useState("");
  const [givenName, setGivenName] = useState("");
  const [familyName, setFamilyName] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [jurisdiction, setJurisdiction] = useState("IN-OD");
  const [providerMessage, setProviderMessage] = useState("");
  const [confirmRepositoryChange, setConfirmRepositoryChange] = useState(false);

  async function loadProviders() {
    try {
      setProviders(await api.providers());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load providers");
    }
  }

  useEffect(() => {
    let active = true;
    async function loadRepositories() {
      try {
        const [repositories, initialJurisdictions, initialRules, integrity] = await Promise.all([
          api.repositories(0, 50),
          api.jurisdictions(),
          api.policyRules(),
          api.verifyLedger(),
        ]);
        if (active) setRepos(repositories);
        if (active) {
          setHasMoreRepos(repositories.length === 50);
          setJurisdictions(initialJurisdictions);
          setPolicyRules(initialRules);
          setLedgerIntegrity(integrity);
        }
      } catch (reason: unknown) {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load repositories");
      }
    }
    async function loadInitialProviders() {
      try {
        const initialProviders = await api.providers();
        if (active) setProviders(initialProviders);
      } catch (reason: unknown) {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load providers");
      }
    }
    void loadRepositories();
    void loadInitialProviders();
    return () => { active = false; };
  }, []);

  async function changeRepository() {
    setRepositoryMessage("");
    if (!changeHealthId.trim() || !changeRepositoryId) {
      setRepositoryMessage("Enter a Health ID and select a target repository.");
      return;
    }
    const target = repos.find((repository) => repository.id === changeRepositoryId);
    if (!target) return;
    if (!confirmRepositoryChange) {
      setConfirmRepositoryChange(true);
      return;
    }
    setConfirmRepositoryChange(false);
    setChangeBusy(true);
    try {
      await api.changeRepository(changeHealthId.trim(), changeRepositoryId);
      setRepositoryMessage(`Repository changed successfully to ${target.name}.`);
      setChangeHealthId("");
      setChangeRepositoryId("");
    } catch (reason: unknown) {
      setRepositoryMessage(reason instanceof Error ? reason.message : "Repository change failed");
    } finally {
      setChangeBusy(false);
    }
  }

  async function migrate() {
    setError("");
    try {
      const created = await api.createTransfer({
        health_id: healthId,
        source_repository_id: source,
        destination_repository_id: destination,
        purpose: "MIGRATION",
        scope: "FHIR",
      });
      setTransfer(created);
      setTransferLookupId(created.id);
      setTransferToken("");
      setTransferMessage("Transfer request created. The patient must authorize it before a token can be issued.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Migration request failed");
    }
  }

  async function refreshTransferStatus() {
    const id = transferLookupId.trim() || transfer?.id;
    if (!id) return;
    try {
      const current = await api.transferStatus(id);
      setTransfer(current);
      setTransferLookupId(current.id);
    } catch (reason: unknown) {
      setTransferMessage(reason instanceof Error ? reason.message : "Unable to load transfer status");
    }
  }

  async function loadMoreRepositories() {
    const nextOffset = repoOffset + 50;
    try {
      const next = await api.repositories(nextOffset, 50);
      setRepos((current) => [...current, ...next]);
      setRepoOffset(nextOffset);
      setHasMoreRepos(next.length === 50);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load more repositories");
    }
  }

  async function addPolicyRule() {
    try {
      const rule = await api.addPolicyRule(policyForm);
      setPolicyRules((current) => [...current, rule].sort((a, b) => a.name.localeCompare(b.name)));
      setPolicyForm((current) => ({ ...current, name: "", description: "" }));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to add policy rule");
    }
  }

  async function deactivatePolicyRule(id: string) {
    try {
      const updated = await api.deactivatePolicyRule(id);
      setPolicyRules((current) => current.map((rule) => rule.id === id ? updated : rule));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to disable policy rule");
    }
  }

  async function issueTransferToken() {
    if (!transfer) return;
    setTransferBusy(true);
    setTransferMessage("");
    try {
      const issued = await api.issueTransferToken(transfer.id);
      setTransferToken(issued.authorization_token);
      setTransfer((current) => current ? { ...current, state: "TRANSFER_AUTH_ISSUED" } : current);
      setTransferMessage(`Token expires ${new Date(issued.expires_at).toLocaleString()}. It is only held in this browser session.`);
    } catch (reason: unknown) {
      setTransferMessage(reason instanceof Error ? reason.message : "Patient authorization is required before token issuance.");
    } finally {
      setTransferBusy(false);
    }
  }

  async function executeTransfer() {
    if (!transfer || !transferToken) return;
    setTransferBusy(true);
    setTransferMessage("");
    try {
      const manifest = await api.executeTransfer(transfer.id, transferToken);
      setTransfer((current) => current ? { ...current, state: "COMPLETED", package_hash: manifest.package_hash } : current);
      setTransferMessage(`Transfer completed. ${manifest.resource_count} resources imported and hash-verified.`);
      setTransferToken("");
    } catch (reason: unknown) {
      setTransferMessage(reason instanceof Error ? reason.message : "FHIR transfer failed");
    } finally {
      setTransferBusy(false);
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
              {hasMoreRepos && <button onClick={() => void loadMoreRepositories()} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">Load more repositories</button>}
            </div>
          </Card>

          <Card title="Change patient repository">
            <div className="space-y-3">
              <Field value={changeHealthId} onChange={(e) => setChangeHealthId(e.target.value)} placeholder="Patient Health ID" />
              <select value={changeRepositoryId} onChange={(e) => setChangeRepositoryId(e.target.value)} className="w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm">
                <option value="">Target repository</option>
                {repos.filter((repository) => repository.status !== "OFFLINE").map((repository) => (
                  <option key={repository.id} value={repository.id}>{repository.code} — {repository.name}</option>
                ))}
              </select>
              <button onClick={() => void changeRepository()} disabled={changeBusy} className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
                {changeBusy ? "Validating repository…" : "Change repository"}
              </button>
              {repositoryMessage && <p className="text-sm text-slate-700">{repositoryMessage}</p>}
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
              {transfer && <div className="rounded-lg border border-cyan-300 bg-cyan-50 p-3 text-sm">
                <p className="font-semibold">Transfer {transfer.id}</p>
                <p className="mt-1">Status: {transfer.state}</p>
                <p className="mt-1 text-slate-700">Give this ID to the patient so they can authorize the request in their portal.</p>
                <button onClick={() => void issueTransferToken()} disabled={transferBusy || transfer.state !== "PATIENT_AUTHORIZED"} className="mt-3 rounded-lg border border-slate-400 px-3 py-2 text-sm font-semibold disabled:opacity-50">
                  Issue one-time transfer token
                </button>
                <button onClick={() => void executeTransfer()} disabled={transferBusy || !transferToken} className="ml-2 mt-3 rounded-lg bg-cyan-800 px-3 py-2 text-sm font-bold text-white disabled:opacity-50">
                  {transferBusy ? "Transferring…" : "Export, verify, and import"}
                </button>
                <button onClick={() => void refreshTransferStatus()} className="ml-2 mt-3 rounded-lg border border-slate-400 px-3 py-2 text-sm font-semibold">Refresh status</button>
                {transferMessage && <p className="mt-2">{transferMessage}</p>}
              </div>}
              <div className="flex gap-2">
                <Field value={transferLookupId} onChange={(event) => setTransferLookupId(event.target.value)} placeholder="Existing transfer ID" />
                <button onClick={() => void refreshTransferStatus()} className="rounded-lg border border-slate-400 px-3 py-2 text-sm font-semibold">Load</button>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Jurisdiction policy rules">
          <div className="grid gap-3 md:grid-cols-2">
            <select value={policyForm.jurisdiction_code} onChange={(event) => setPolicyForm((current) => ({ ...current, jurisdiction_code: event.target.value }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              {jurisdictions.map((item) => <option key={item.id} value={item.code}>{item.code} — {item.name}</option>)}
            </select>
            <Field value={policyForm.name} onChange={(event) => setPolicyForm((current) => ({ ...current, name: event.target.value }))} placeholder="Rule name" />
            <Field value={policyForm.purpose} onChange={(event) => setPolicyForm((current) => ({ ...current, purpose: event.target.value }))} placeholder="Purpose" />
            <Field value={policyForm.scope} onChange={(event) => setPolicyForm((current) => ({ ...current, scope: event.target.value }))} placeholder="Scope" />
            <select value={policyForm.effect} onChange={(event) => setPolicyForm((current) => ({ ...current, effect: event.target.value as "ALLOW" | "DENY" }))} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="ALLOW">Allow</option><option value="DENY">Deny</option>
            </select>
            <Field value={policyForm.description} onChange={(event) => setPolicyForm((current) => ({ ...current, description: event.target.value }))} placeholder="Description (optional)" />
          </div>
          <button onClick={() => void addPolicyRule()} disabled={!policyForm.name.trim()} className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Add policy rule</button>
          <ul className="mt-4 space-y-2">
            {policyRules.map((rule) => {
              const jurisdictionName = jurisdictions.find((item) => item.id === rule.jurisdiction_id);
              return <li key={rule.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-300 p-3 text-sm">
                <span><strong>{rule.name}</strong> · {jurisdictionName?.code ?? "Unknown"} · {rule.purpose}/{rule.scope} · {rule.effect} · {rule.active ? "Active" : "Disabled"}</span>
                {rule.active && <button onClick={() => void deactivatePolicyRule(rule.id)} className="rounded-lg border border-red-300 px-3 py-1 text-xs font-semibold text-red-700">Disable</button>}
              </li>;
            })}
          </ul>
        </Card>
        <Card title="Trust ledger integrity">
          {ledgerIntegrity ? (
            <div className={ledgerIntegrity.valid ? "rounded-lg border border-emerald-300 bg-emerald-50 p-4" : "rounded-lg border border-red-300 bg-red-50 p-4"}>
              <p className="font-bold">{ledgerIntegrity.valid ? "Ledger verified" : "Ledger integrity check failed"}</p>
              <p className="mt-1 text-sm">{ledgerIntegrity.entries_checked} entries checked</p>
            </div>
          ) : <p className="text-sm text-slate-600">Ledger verification is loading.</p>}
          <button onClick={() => void api.verifyLedger().then(setLedgerIntegrity).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Ledger verification failed"))} className="mt-3 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold">Verify now</button>
        </Card>
      </div>

      {error && (
        <p className="mt-5 rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-800">
          {error}
        </p>
      )}
      {confirmRepositoryChange && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4">
        <section role="dialog" aria-modal="true" aria-labelledby="repository-confirm-title" className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <h2 id="repository-confirm-title" className="text-lg font-bold">Confirm repository switch</h2>
          <p className="mt-2 text-sm text-slate-700">Switch {changeHealthId} to {repos.find((item) => item.id === changeRepositoryId)?.name}? Existing records are not moved.</p>
          <div className="mt-5 flex justify-end gap-3">
            <button onClick={() => setConfirmRepositoryChange(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm">Cancel</button>
            <button onClick={() => void changeRepository()} disabled={changeBusy} className="rounded-lg bg-cyan-800 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Confirm switch</button>
          </div>
        </section>
      </div>}
    </PortalShell>
  );
}
