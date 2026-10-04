"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { completeLogin, ROLE_CONFIG, type UserRole } from "@/lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const started = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    const keycloakError = params.get("error");

    if (keycloakError) {
      setError(
        params.get("error_description") ?? "Keycloak login was cancelled.",
      );
      return;
    }

    if (!code || !state) {
      setError("Missing authentication response. Please start login again.");
      return;
    }

    void completeLogin(code, state)
      .then((role: UserRole) => router.replace(ROLE_CONFIG[role].portal))
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error ? reason.message : "Login failed.",
        ),
      );
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-8 text-center text-white shadow-2xl">
        {error ? (
          <>
            <h1 className="text-xl font-bold text-red-300">Login failed</h1>
            <p className="mt-2 text-sm text-slate-300">{error}</p>
            <a
              href="/login"
              className="mt-5 inline-block rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-950"
            >
              Return to sign in
            </a>
          </>
        ) : (
          <>
            <h1 className="text-xl font-bold">Completing secure sign-in…</h1>
            <p className="mt-2 text-sm text-slate-300">
              Verifying your HealthNet account.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
