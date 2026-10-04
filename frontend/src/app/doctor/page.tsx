"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Card, Field, PortalShell } from "@/components/portal-shell";
export default function DoctorPortal() {
  const [healthId,setHealthId]=useState(""); const [purpose,setPurpose]=useState("TREATMENT"); const [scope,setScope]=useState("clinical"); const [result,setResult]=useState<unknown>(null); const [error,setError]=useState("");
  async function load(){setError("");try{setResult(await api.longitudinal(healthId,purpose,scope))}catch(e){setError(e instanceof Error?e.message:"Authorization or retrieval failed")}}
  return <PortalShell requiredRole="provider" title="Doctor Portal" description="Federated longitudinal access is subject to authentication, consent and jurisdiction policy."><Card title="Authorized patient view"><div className="grid gap-3 md:grid-cols-3"><Field value={healthId} onChange={e=>setHealthId(e.target.value)} placeholder="Health ID"/><Field value={purpose} onChange={e=>setPurpose(e.target.value)} placeholder="Purpose"/><Field value={scope} onChange={e=>setScope(e.target.value)} placeholder="Scope"/></div><button onClick={load} className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white">Request longitudinal view</button>{error&&<p className="mt-3 text-sm text-red-600">{error}</p>}{result !== null &&<pre className="mt-4 max-h-[520px] overflow-auto rounded-lg bg-slate-50 p-4 text-xs">{JSON.stringify(result,null,2)}</pre>}</Card></PortalShell>;
}