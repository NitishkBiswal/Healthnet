"use client";

import Link from "next/link";

import { ROLE_CONFIG, type UserRole } from "@/lib/auth";

const roles: UserRole[] = ["patient", "provider", "admin", "auditor"];

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12 text-white">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="text-lg font-bold text-white">
          HealthNet
        </Link>
        <div className="mt-10 max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
            Secure access
          </p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight">
            Choose your HealthNet portal
          </h1>
          <p className="mt-4 text-slate-300">
            Each portal has its own role check. You will authenticate through
            HealthNet Keycloak before access is granted.
          </p>
        </div>
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {roles.map((role) => (
            <Link
              key={role}
              href={"/login/" + role}
              className="rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-xl transition hover:-translate-y-0.5 hover:border-cyan-400 hover:bg-slate-800"
            >
              <h2 className="text-xl font-bold text-white">
                {ROLE_CONFIG[role].label} Login
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                {ROLE_CONFIG[role].description}
              </p>
              <span className="mt-5 inline-block text-sm font-semibold text-cyan-300">
                Continue →
              </span>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
