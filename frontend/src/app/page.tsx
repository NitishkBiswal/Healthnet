import Link from "next/link";

const portals = [
  { path: "patient", title: "Patient Portal", desc: "Manage your health identity, consent and medical records.", detail: "For patients", icon: "01" },
  { path: "provider", title: "Doctor Workspace", desc: "Access clinical records shared with you by your patients.", detail: "For healthcare providers", icon: "02" },
  { path: "admin", title: "Admin Workspace", desc: "Manage healthcare repositories, providers and EHR migration.", detail: "For administrators", icon: "03" },
  { path: "auditor", title: "Auditor Workspace", desc: "Review audit events and verify integrity across the network.", detail: "For auditors", icon: "04" },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <Link href="/" className="text-xl font-bold tracking-tight text-slate-900">HealthNet</Link>
          <span className="hidden text-sm font-medium text-slate-500 sm:block">Federated health identity &amp; interoperability</span>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-6 py-14 md:py-20">
        <section className="mb-12 max-w-3xl">
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-blue-700">Connected care, trusted access</p>
          <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Federated Health Network</h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600">
            One permanent identity, distributed clinical records and consent-gated access — connected through FHIR interoperability and auditable trust.
          </p>
        </section>
        <section aria-label="Choose a workspace" className="grid gap-5 sm:grid-cols-2">
          {portals.map((portal) => (
            <Link key={portal.path} href={"/login/" + portal.path}
              className="group rounded-2xl border border-slate-200 bg-white p-7 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">{portal.detail}</p>
                  <h2 className="mt-2 text-xl font-bold text-slate-900">{portal.title}</h2>
                </div>
                <span className="rounded-xl bg-slate-100 px-3 py-2 text-sm font-bold text-slate-500">{portal.icon}</span>
              </div>
              <p className="mt-3 max-w-md text-sm leading-6 text-slate-600">{portal.desc}</p>
              <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-blue-700 group-hover:text-blue-800">Continue to sign in <span aria-hidden="true">→</span></span>
            </Link>
          ))}
        </section>
        <div className="mt-8 flex flex-col gap-2 rounded-xl border border-blue-100 bg-blue-50 px-5 py-4 text-sm text-slate-700 sm:flex-row sm:items-center">
          <span className="font-bold text-blue-800">Secure by design</span>
          <span>Authentication is managed by Keycloak using OpenID Connect and role-based access control.</span>
        </div>
      </div>
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-5 text-xs text-slate-500">HealthNet · Federated healthcare interoperability</div>
      </footer>
    </main>
  );
}
