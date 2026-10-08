"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, type AuthorizedPatient, type Principal } from "@/lib/api";
import { Card, PortalShell } from "@/components/portal-shell";

export default function DoctorPortal() {
  const router = useRouter();
  const [healthId, setHealthId] = useState("");
  const [purpose, setPurpose] = useState("TREATMENT");
  const [scope, setScope] = useState("clinical");
  const [error, setError] = useState("");
  const [authorized, setAuthorized] = useState<AuthorizedPatient[]>([]);
  const [principal, setPrincipal] = useState<Principal | null>(null);

  async function loadPrincipal() {
    try {
      setPrincipal(await api.currentPrincipal());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load doctor identity");
    }
  }

  async function loadAuthorized() {
    try {
      setAuthorized(await api.authorizedPatients());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to load authorized patients");
    }
  }

  useEffect(() => {
    void loadPrincipal();
    void loadAuthorized();
  }, []);

  function openLongitudinalView() {
    setError("");
    if (!healthId) {
      setError("Select an authorized patient first.");
      return;
    }
    router.push(
      `/doctor/longitudinal?health_id=${encodeURIComponent(healthId)}&purpose=${encodeURIComponent(purpose)}&scope=${encodeURIComponent(scope)}`,
    );
  }

  return (
    <PortalShell
      requiredRole="provider"
      title="Doctor Portal"
      description="Review patients who have granted you access and open their clinical history when needed."
    >
      <div className="space-y-5">
        <Card title="Your HealthNet Provider ID">
          <p className="text-sm text-slate-700">
            Patients use this Provider ID when granting you consent.
          </p>
          <p className="mt-2 rounded-lg bg-cyan-50 px-3 py-2 font-mono text-sm font-bold text-slate-950">
            {principal?.provider_id || "Not linked to a HealthNet provider"}
          </p>
          {!principal?.provider_id && principal?.subject && (
            <div className="mt-3 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950">
              <p className="font-semibold">This account is not linked to a HealthNet Provider record yet.</p>
              <p className="mt-1 break-all font-mono">{principal.subject}</p>
            </div>
          )}
        </Card>

        <Card title="Patients who have granted you access">
          {authorized.length === 0 ? (
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-sm font-medium text-slate-700">
                No patients have currently granted you access.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {authorized.map((patient) => {
                const selected = healthId === patient.health_id;
                return (
                  <button
                    key={patient.consent_id}
                    onClick={() => {
                      setHealthId(patient.health_id);
                      setPurpose(patient.purpose);
                      setScope(patient.scopes[0] ?? "clinical");
                      setError("");
                    }}
                    className={`block w-full rounded-xl border-2 p-4 text-left transition ${
                      selected
                        ? "border-cyan-600 bg-cyan-50"
                        : "border-slate-200 bg-white hover:border-slate-400 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-base font-bold text-slate-950">
                        {patient.given_name} {patient.family_name}
                      </span>
                      <span className="rounded-full bg-white px-3 py-1 font-mono text-xs font-bold text-slate-700">
                        {patient.health_id}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-600">
                      Access purpose: <span className="font-semibold">{patient.purpose}</span>
                      {" · "}
                      Permission: <span className="font-semibold">{patient.scopes.join(", ")}</span>
                    </p>
                    <p className="mt-2 text-xs font-semibold text-cyan-800">
                      {selected ? "Patient selected" : "Select patient to view record"}
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

        <Card title="Patient record">
          {healthId ? (
            <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-5">
              <p className="text-xs font-bold uppercase tracking-wide text-cyan-800">Selected patient</p>
              <h2 className="mt-1 text-xl font-bold text-slate-950">
                {authorized.find((patient) => patient.health_id === healthId)?.given_name}{" "}
                {authorized.find((patient) => patient.health_id === healthId)?.family_name}
              </h2>
              <p className="mt-1 font-mono text-sm text-slate-700">{healthId}</p>
              <p className="mt-3 text-sm text-slate-700">
                Open the dedicated clinical view to review the patient's demographics, current record repository, and clinical history.
              </p>
              <button
                onClick={openLongitudinalView}
                className="mt-4 rounded-lg bg-slate-950 px-5 py-2.5 text-sm font-bold text-white hover:bg-slate-800"
              >
                Open Longitudinal Record →
              </button>
            </div>
          ) : (
            <div className="rounded-lg bg-slate-50 p-5">
              <p className="text-sm font-semibold text-slate-700">
                Select a patient above to open their authorized clinical record.
              </p>
              <p className="mt-1 text-xs text-slate-500">
                The detailed record opens on a separate page so the doctor dashboard stays uncluttered.
              </p>
            </div>
          )}
          {error && <p className="mt-3 text-sm font-semibold text-red-600">{error}</p>}
        </Card>
      </div>
    </PortalShell>
  );
}
