"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const portals = [
  ["/patient", "Patient", "Identity, consent, emergency profile"],
  ["/doctor", "Doctor", "Authorized longitudinal health view"],
  ["/admin", "Admin", "Repositories and migration workflows"],
  ["/auditor", "Auditor", "Audit, provenance and integrity"],
];

export function PortalShell({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  const [token, setToken] = useState("");
  useEffect(() => setToken(localStorage.getItem("healthnet_token") ?? ""), []);
  function saveToken(value: string) {
    setToken(value);
    if (value) localStorage.setItem("healthnet_token", value);
    else localStorage.removeItem("healthnet_token");
  }
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-5 md:flex-row md:items-center md:justify-between">
          <div><Link href="/" className="text-xl font-bold">HealthNet</Link><p className="text-xs text-slate-500">Federated health identity & interoperability</p></div>
          <nav className="flex flex-wrap gap-2">{portals.map(([href,label]) => <Link key={href} href={href} className="rounded-lg border px-3 py-2 text-sm hover:bg-slate-50">{label}</Link>)}</nav>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 rounded-xl border bg-white p-5">
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
          <label className="mt-4 block text-xs font-medium text-slate-600">Bearer token (Keycloak)</label>
          <input value={token} onChange={(e) => saveToken(e.target.value)} placeholder="Paste access token for protected actions" className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
        </div>
        {children}
      </div>
    </main>
  );
}

export function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl border bg-white p-5 shadow-sm"><h2 className="mb-4 font-semibold">{title}</h2>{children}</section>;
}

export function Field(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className="w-full rounded-lg border px-3 py-2 text-sm" />;
}
