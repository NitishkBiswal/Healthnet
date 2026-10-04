"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";
export default function AuditorPortal() {
  const [healthId,setHealthId]=useState(""); const [events,setEvents]=useState<unknown>(null); const [integrity,setIntegrity]=useState<unknown>(null); const [error,setError]=useState("");
  async function audit(){setError("");try{setEvents(await api.audits(healthId))}catch(e){setError(e instanceof Error?e.message:"Audit access denied")}}
  async function verify(){setError("");try{setIntegrity(await api.verifyLedger())}catch(e){setError(e instanceof Error?e.message:"Ledger verification failed")}}
  return <PortalShell title="Auditor Portal" description="Read-only oversight of audit trails and trust integrity."><div className="grid gap-5 lg:grid-cols-2"><Card title="Patient audit trail"><div className="flex gap-2"><Field value={healthId} onChange={e=>setHealthId(e.target.value)} placeholder="Health ID"/><button onClick={audit} className="rounded-lg bg-slate-900 px-4 text-sm text-white">Inspect</button></div>{events !== null &&<pre className="mt-4 max-h-[500px] overflow-auto rounded-lg bg-slate-50 p-4 text-xs">{JSON.stringify(events,null,2)}</pre>}</Card><Card title="Trust ledger integrity"><button onClick={verify} className="rounded-lg border px-4 py-2 text-sm">Verify chain</button>{integrity !== null &&<pre className="mt-4 rounded-lg bg-slate-50 p-4 text-xs">{JSON.stringify(integrity,null,2)}</pre>}{error&&<p className="mt-3 text-sm text-red-600">{error}</p>}</Card></div></PortalShell>;
}