"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { beginLogin, beginRegistration, ROLE_CONFIG, type UserRole } from "@/lib/auth";

const validRoles: UserRole[] = ["patient", "provider", "admin", "auditor"];

export default function RoleLoginPage() {
  const params = useParams<{ role: string }>();
  const role = params.role as UserRole;
  const config = validRoles.includes(role) ? ROLE_CONFIG[role] : null;
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  if (!config) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6 text-slate-900">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-bold">Portal not found</h1>
          <Link href="/login" className="mt-4 inline-block text-sm font-semibold text-blue-700 hover:text-blue-800">
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
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6 py-10 text-slate-900">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
        <Link href="/login" className="inline-flex items-center text-sm font-semibold text-blue-700 transition hover:text-blue-800">
          <span aria-hidden="true" className="mr-2">←</span> Choose portal
        </Link>
        <div className="mt-9">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">
            Secure sign-in
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
            {config.label} Portal
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {config.description}
          </p>
        </div>
        <div className="mt-7 rounded-xl border border-blue-100 bg-blue-50 px-4 py-4 text-sm leading-6 text-slate-700">
          You will be securely redirected to HealthNet Keycloak. Your account
          role is checked before you enter this portal.
        </div>
        {role === "patient" && (
          <p className="mt-5 text-sm leading-6 text-slate-600">
            First time here? After sign-in, choose <strong className="font-semibold text-slate-900">Get my Health ID</strong> to register your identity.
          </p>
        )}
        {error && (
          <p role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}
        <button
          onClick={login}
          disabled={starting}
          className="mt-7 w-full rounded-lg bg-blue-700 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {starting ? "Redirecting…" : "Sign in as " + config.label}
        </button>
        {role === "patient" && (
          <div className="mt-6 border-t border-slate-200 pt-6 text-center">
            <p className="text-sm text-slate-500">First time using HealthNet?</p>
            <button
              onClick={() => void beginRegistration()}
              className="mt-2 text-sm font-semibold text-blue-700 transition hover:text-blue-800"
            >
              Create a Patient Account
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
