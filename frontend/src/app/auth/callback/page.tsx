"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { completeLogin, ROLE_CONFIG, type UserRole } from "@/lib/auth";
export default function AuthCallbackPage() {
  const router = useRouter(); const [error, setError] = useState("");
  useEffect(() => { const params = new URLSearchParams(window.location.search); const code = params.get("code"); const state = params.get("state"); const keycloakError = params.get("error");
    if (keycloakError) { setError(params.get("error_description") ?? "Keycloak login was cancelled."); return; }
    if (!code || !state) { setError("Missing authentication response. Please start login again."); return; }
    void completeLogin(code, state).then((role: UserRole) => router.replace(ROLE_CONFIG[role].portal)).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Login failed."));
  }, [router]);
  return <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6"><div className="max-w-md rounded-xl border bg-white p-8 text-center shadow-sm">{error ? <><h1 className="text-xl font-bold text-red-700">Login failed</h1><p className="mt-2 text-sm text-slate-600">{error}</p><a href="/" className="mt-5 inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm text-white">Return to HealthNet</a></> : <><h1 className="text-xl font-bold">Completing secure sign-in…</h1><p className="mt-2 text-sm text-slate-600">Verifying your HealthNet account.</p></>}</div></main>;
}