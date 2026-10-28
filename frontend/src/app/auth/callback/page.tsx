"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { completeLogin, ROLE_CONFIG, type UserRole } from "@/lib/auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const started = useRef(false);
  const [initialParams] = useState(() =>
    typeof window === "undefined" ? new URLSearchParams() : new URLSearchParams(window.location.search),
  );
  const [error, setError] = useState(() => {
    const keycloakError = initialParams.get("error");
    if (keycloakError) return initialParams.get("error_description") ?? "Keycloak login was cancelled.";
    if (!initialParams.get("code") || !initialParams.get("state")) {
      return "Missing authentication response. Please start login again.";
    }
    return "";
  });

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const code = initialParams.get("code");
    const state = initialParams.get("state");
    if (!code || !state || initialParams.get("error") || error) return;

    void completeLogin(code, state)
      .then((role: UserRole) => router.replace(ROLE_CONFIG[role].portal))
      .catch((reason: unknown) =>
        setError(
          reason instanceof Error ? reason.message : "Login failed.",
        ),
      );
  }, [error, initialParams, router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-8 text-center text-white shadow-2xl">
        {error ? (
          <>
            <h1 className="text-xl font-bold text-red-300">Login failed</h1>
            <p className="mt-2 text-sm text-slate-300">{error}</p>
            <Link
              href="/login"
              className="mt-5 inline-block rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-950"
            >
              Return to sign in
            </Link>
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
