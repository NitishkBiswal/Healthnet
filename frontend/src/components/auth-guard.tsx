"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { getSessionRole, type UserRole } from "@/lib/auth";
export function AuthGuard({ requiredRole, children }: { requiredRole: UserRole; children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<"checking" | "allowed" | "denied">("checking");
  const [message, setMessage] = useState("");
  useEffect(() => { let active = true; async function verify() {
    const role = getSessionRole();
    if (!role) { router.replace("/login/" + requiredRole); return; }
    if (role !== requiredRole) { if (active) { setMessage("This account is signed in as " + role + ", not " + requiredRole + "."); setStatus("denied"); } return; }
    try { await api.currentPrincipal(); if (active) setStatus("allowed"); } catch { if (active) { setMessage("Your session is invalid or has expired. Please sign in again."); setStatus("denied"); } }
  } void verify(); return () => { active = false; }; }, [requiredRole, router]);
  if (status === "checking") return <main className="flex min-h-screen items-center justify-center bg-slate-50"><div className="rounded-xl border bg-white p-8 text-center shadow-sm"><p className="font-semibold">Checking your HealthNet session…</p></div></main>;
  if (status === "denied") return <main className="flex min-h-screen items-center justify-center bg-slate-50"><div className="max-w-md rounded-xl border bg-white p-8 text-center shadow-sm"><h1 className="text-xl font-bold">Access denied</h1><p className="mt-2 text-sm text-slate-600">{message}</p><button onClick={() => router.replace("/login/" + requiredRole)} className="mt-5 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white">Sign in</button></div></main>;
  return <>{children}</>;
}