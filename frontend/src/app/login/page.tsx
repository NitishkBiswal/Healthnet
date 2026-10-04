"use client";
import Link from "next/link";
import { ROLE_CONFIG, type UserRole } from "@/lib/auth";
const roles: UserRole[] = ["patient", "provider", "admin", "auditor"];
export default function LoginSelectionPage() {
  return <main className="min-h-screen bg-slate-50 px-6 py-16"><div className="mx-auto max-w-4xl"><div className="text-center"><p className="text-sm font-semibold uppercase tracking-wider text-slate-500">HealthNet</p><h1 className="mt-2 text-4xl font-bold">Choose your portal</h1><p className="mx-auto mt-3 max-w-2xl text-slate-600">Each HealthNet role has its own sign-in experience and permissions.</p></div><div className="mt-10 grid gap-5 md:grid-cols-2">{roles.map((role) => <Link key={role} href={"/login/" + role} className="rounded-2xl border bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"><h2 className="text-xl font-semibold">{ROLE_CONFIG[role].label} Login</h2><p className="mt-2 text-sm text-slate-600">{ROLE_CONFIG[role].description}</p><span className="mt-5 inline-block text-sm font-medium">Continue →</span></Link>)}</div></div></main>;
}