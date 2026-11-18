"use client";

import Link from "next/link";
import { ROLE_CONFIG, type UserRole } from "@/lib/auth";

const roles: UserRole[] = ["patient", "provider", "admin", "auditor"];

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-5">
          <Link href="/" className="text-xl font-bold tracking-tight text-slate-900">HealthNet</Link>
          <p className="text-xs text-slate-500">Federated health identity &amp; interoperability</p>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-6 py-12 md:py-16">
        <div className="max-w-3xl">
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700">Secure access</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Choose your HealthNet workspace</h1>
          <p className="mt-4 leading-7 text-slate-600">
            Select the workspace that matches your role. HealthNet verifies your identity and permissions before granting access.
          </p>
        </div>
        <div className="mt-9 grid gap-5 sm:grid-cols-2">
          {roles.map((role, index) => (
            <Link key={role} href={"/login/" + role}
              className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900">{ROLE_CONFIG[role].label} Workspace</h2>
                <span className="rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-bold text-slate-500">0{index + 1}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600">{ROLE_CONFIG[role].description}</p>
              <span className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-blue-700 group-hover:text-blue-800">Continue <span aria-hidden="true">→</span></span>
            </Link>
          ))}
        </div>
        <p className="mt-8 rounded-xl border border-blue-100 bg-blue-50 px-5 py-4 text-sm text-slate-700">
          <span className="font-semibold text-blue-800">Your security matters.</span> Sign-in is handled by HealthNet Keycloak using OpenID Connect.
        </p>
      </div>
    </main>
  );
}
