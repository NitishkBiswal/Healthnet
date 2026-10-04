"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { beginLogin, ROLE_CONFIG, type UserRole } from "@/lib/auth";

const validRoles: UserRole[] = ["patient", "provider", "admin", "auditor"];

export default function RoleLoginPage() {
  const params = useParams<{ role: string }>();
  const role = params.role as UserRole;
  const config = validRoles.includes(role) ? ROLE_CONFIG[role] : null;
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  if (!config) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-white">
        <div className="rounded-2xl border border-slate-700 bg-slate-900 p-8 text-center shadow-2xl">
          <h1 className="text-xl font-bold">Portal not found</h1>
          <Link href="/login" className="mt-4 inline-block text-sm text-cyan-300 underline">
            Choose another portal
          </Link>
        </div>
      </main>
    );
  }

  async function login() {
    setStarting(true);
    setError("");
    try {
      await beginLogin(role);
    } catch (reason: unknown) {
      setStarting(false);
      setError(reason instanceof Error ? reason.message : "Unable to start login.");
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 py-10 text-white">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-8 shadow-2xl">
        <Link href="/login" className="text-sm font-semibold text-cyan-300">
          ← Choose portal
        </Link>
        <p className="mt-8 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
          Secure sign-in
        </p>
        <h1 className="mt-2 text-3xl font-bold">{config.label} Portal</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          {config.description}
        </p>
        <div className="mt-6 rounded-xl border border-slate-700 bg-slate-800 p-4 text-sm leading-6 text-slate-200">
          You will be securely redirected to HealthNet Keycloak. Your account
          role is checked before you enter this portal.
        </div>
        {role === "patient" && (
          <p className="mt-4 text-sm text-slate-400">
            First time here? After sign-in, choose <strong className="text-white">Get my Health ID</strong> to register your identity.
          </p>
        )}
        {error && (
          <p className="mt-4 rounded-lg border border-red-800 bg-red-950/60 p-3 text-sm text-red-200">
            {error}
          </p>
        )}
        <button
          onClick={login}
          disabled={starting}
          className="mt-6 w-full rounded-lg bg-cyan-400 px-4 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-60"
        >
          {starting ? "Redirecting…" : "Sign in as " + config.label}
        </button>
      </div>
    </main>
  );
}
