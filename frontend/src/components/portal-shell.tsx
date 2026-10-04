"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/auth-guard";
import { getUserClaims, logout, type UserRole } from "@/lib/auth";

const portals = [["/patient", "Patient"], ["/doctor", "Doctor"], ["/admin", "Admin"], ["/auditor", "Auditor"]];

export function PortalShell({ title, description, requiredRole, children }: { title: string; description: string; requiredRole: UserRole; children: React.ReactNode }) {
  const [claims, setClaims] = useState<{ name?: string; email?: string }>({});
  useEffect(() => setClaims(getUserClaims()), []);

  return (
    <AuthGuard requiredRole={requiredRole}>
      <main className="min-h-screen bg-slate-100 text-slate-950">
        <header className="border-b-2 border-slate-300 bg-white">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-5 md:flex-row md:items-center md:justify-between">
            <div>
              <Link href="/" className="text-xl font-bold text-slate-950">HealthNet</Link>
              <p className="text-xs font-medium text-slate-600">Federated health identity & interoperability</p>
            </div>
            <nav className="flex flex-wrap gap-2">
              {portals.map(([href, label]) => (
                <Link key={href} href={href} className="rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-semibold text-slate-900 hover:border-slate-700 hover:bg-slate-100">
                  {label}
                </Link>
              ))}
              <button onClick={logout} className="rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-semibold text-slate-900 hover:border-slate-700 hover:bg-slate-100">
                Logout
              </button>
            </nav>
          </div>
        </header>

        <div className="mx-auto max-w-7xl px-6 py-8">
          <div className="mb-6 rounded-xl border-2 border-slate-300 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h1 className="text-2xl font-bold text-slate-950">{title}</h1>
                <p className="mt-1 text-sm font-medium text-slate-700">{description}</p>
              </div>
              <div className="text-right text-xs text-slate-700">
                <p className="font-bold text-slate-950">{claims.name ?? "HealthNet user"}</p>
                <p>{claims.email ?? ""}</p>
              </div>
            </div>
          </div>
          {children}
        </div>
      </main>
    </AuthGuard>
  );
}

export function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border-2 border-slate-300 bg-white p-5 shadow-sm">
      <h2 className="mb-4 font-semibold text-slate-950">{title}</h2>
      {children}
    </section>
  );
}

export function Field(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={"w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-950 placeholder:text-slate-600 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-300 " + (props.className ?? "")}
    />
  );
}
