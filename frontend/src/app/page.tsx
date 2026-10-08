import Link from "next/link";

const portals = [
  ["patient", "Patient Portal", "Identity, consent and emergency profile"],
  ["provider", "Doctor Portal", "Authorized federated longitudinal health view"],
  ["admin", "Admin Portal", "Repositories and EHR migration"],
  ["auditor", "Auditor Portal", "Audit and integrity verification"],
];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="mb-12 text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-cyan-400">
            HealthNet
          </p>
          <h1 className="mt-2 text-4xl font-bold text-white">
            Federated Health Network
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-slate-300">
            One permanent identity, distributed clinical records, consent-gated
            access, FHIR interoperability and auditable trust.
          </p>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          {portals.map(([path, title, desc]) => (
            <Link
              key={path}
              href={"/login/" + path}
              className="rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-lg transition hover:-translate-y-0.5 hover:border-cyan-500 hover:shadow-cyan-950/40"
            >
              <h2 className="text-xl font-semibold text-white">{title}</h2>
              <p className="mt-2 text-sm text-slate-300">{desc}</p>
              <span className="mt-5 inline-block text-sm font-semibold text-cyan-400">
                Secure sign-in →
              </span>
            </Link>
          ))}
        </div>

        <div className="mt-8 rounded-xl border border-slate-700 bg-slate-900 p-5 text-sm text-slate-300">
          <strong className="text-cyan-400">Security:</strong> authentication
          is handled by Keycloak using browser-based OpenID Connect with
          role-specific access control.
        </div>
      </div>
    </main>
  );
}
