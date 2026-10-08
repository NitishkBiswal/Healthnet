"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, type AuthorizedPatient, type CurrentRecordLocation, type Patient, type Principal } from "@/lib/api";
import { Card, PortalShell } from "@/components/portal-shell";

type LongitudinalRecord = {
  repository?: string;
  resource_type?: string;
  resource?: Record<string, unknown>;
};

type LongitudinalResponse = {
  health_id?: string;
  current_repository?: {
    code?: string;
    name?: string;
    jurisdiction?: string;
    endpoint?: string;
  };
  completeness?: string;
  records?: LongitudinalRecord[];
  repositories_checked?: number;
  repositories_available?: number;
  errors?: string[];
};

function getDisplayValue(resource: Record<string, unknown>, path: string[]): string | null {
  let value: unknown = resource;
  for (const key of path) {
    if (!value || typeof value !== "object") return null;
    value = (value as Record<string, unknown>)[key];
  }
  return typeof value === "string" || typeof value === "number" ? String(value) : null;
}

function RecordCard({ record }: { record: LongitudinalRecord }) {
  const resource = record.resource ?? {};
  const type = record.resource_type ?? String(resource.resourceType ?? "Clinical record");

  let title = type;
  let summary = "";
  let date = getDisplayValue(resource, ["recordedDate"]) ?? getDisplayValue(resource, ["effectiveDateTime"]);

  if (type === "Encounter") {
    title = "Clinical Visit";
    summary = "Outpatient encounter";
    date = getDisplayValue(resource, ["period", "start"]) ?? date;
  } else if (type === "Condition") {
    title = "Condition";
    summary = getDisplayValue(resource, ["code", "coding", "0", "display"]) ?? "Recorded health condition";
    date = getDisplayValue(resource, ["recordedDate"]) ?? date;
  } else if (type === "Observation") {
    const display = getDisplayValue(resource, ["code", "coding", "0", "display"]) ?? "Clinical measurement";
    title = display;
    const components = Array.isArray(resource.component) ? resource.component : [];
    if (components.length) {
      summary = components.map((item) => {
        if (!item || typeof item !== "object") return "";
        const component = item as Record<string, unknown>;
        const name = getDisplayValue(component, ["code", "coding", "0", "display"]) ?? "Measurement";
        const value = getDisplayValue(component, ["valueQuantity", "value"]);
        const unit = getDisplayValue(component, ["valueQuantity", "unit"]);
        return value ? `${name}: ${value} ${unit ?? ""}` : name;
      }).filter(Boolean).join(" · ");
    } else {
      const value = getDisplayValue(resource, ["valueQuantity", "value"]);
      const unit = getDisplayValue(resource, ["valueQuantity", "unit"]);
      summary = value ? `${value} ${unit ?? ""}` : "Clinical observation";
    }
  } else if (type === "MedicationRequest") {
    title = "Medication";
    summary = getDisplayValue(resource, ["medicationCodeableConcept", "coding", "0", "display"]) ?? "Medication order";
    const dosage = Array.isArray(resource.dosageInstruction) ? resource.dosageInstruction[0] : null;
    if (dosage && typeof dosage === "object") {
      summary += ` · ${getDisplayValue(dosage as Record<string, unknown>, ["text"]) ?? ""}`;
    }
  } else if (type === "Patient") {
    title = "Patient record";
    summary = "Patient identity record";
  }

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-cyan-700">{title}</p>
          <p className="mt-1 text-base font-semibold text-slate-950">{summary || "Clinical record"}</p>
        </div>
        {date && (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
            {new Date(date).toLocaleString()}
          </span>
        )}
      </div>
    </article>
  );
}

export default function DoctorLongitudinalView() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const healthId = searchParams.get("health_id") ?? "";
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [patient, setPatient] = useState<Patient | null>(null);
  const [location, setLocation] = useState<CurrentRecordLocation | null>(null);
  const [view, setView] = useState<LongitudinalResponse | null>(null);
  const [authorized, setAuthorized] = useState<AuthorizedPatient[]>([]);
  const [error, setError] = useState("");

  const patientSummary = useMemo(
    () => authorized.find((item) => item.health_id === healthId),
    [authorized, healthId],
  );

  useEffect(() => {
    if (!healthId) {
      setError("No patient was selected.");
      return;
    }

    async function load() {
      try {
        const [principalData, authorizedData, patientData, locationData, longitudinalData] = await Promise.all([
          api.currentPrincipal(),
          api.authorizedPatients(),
          api.patient(healthId),
          api.currentRecordLocation(healthId),
          api.longitudinal(healthId, patientSummary?.purpose ?? "TREATMENT", patientSummary?.scopes?.[0] ?? "clinical"),
        ]);
        setPrincipal(principalData);
        setAuthorized(authorizedData);
        setPatient(patientData);
        setLocation(locationData);
        setView(longitudinalData as LongitudinalResponse);
      } catch (reason: unknown) {
        setError(reason instanceof Error ? reason.message : "Unable to load the patient's longitudinal record");
      }
    }

    void load();
  }, [healthId, patientSummary?.purpose, patientSummary?.scopes]);

  const records = view?.records ?? [];
  const errors = view?.errors ?? [];

  return (
    <PortalShell
      requiredRole="provider"
      title="Patient Longitudinal Record"
      description="A clinician-friendly view of the patient's authorized clinical history."
    >
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={() => router.push("/doctor")}
          className="rounded-lg border-2 border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-900 hover:bg-slate-50"
        >
          ← Back to Doctor Dashboard
        </button>
        <span className="text-xs font-medium text-slate-600">
          Signed in as {principal?.provider_name ?? "HealthNet Provider"}
        </span>
      </div>

      {error ? (
        <Card title="Unable to open patient record">
          <p className="text-sm text-red-700">{error}</p>
        </Card>
      ) : (
        <div className="space-y-5">
          <Card title="Patient">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Name</p>
                <p className="mt-1 font-semibold text-slate-950">
                  {patient ? `${patient.given_name} ${patient.family_name}` : patientSummary ? `${patientSummary.given_name} ${patientSummary.family_name}` : "Loading..."}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Health ID</p>
                <p className="mt-1 font-mono font-semibold text-slate-950">{healthId}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Date of birth</p>
                <p className="mt-1 font-semibold text-slate-950">{patient?.date_of_birth ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Sex</p>
                <p className="mt-1 font-semibold text-slate-950">{patient?.sex ?? "—"}</p>
              </div>
            </div>
          </Card>

          <Card title="Record location">
            <div className="rounded-xl border border-cyan-200 bg-cyan-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wide text-cyan-800">Current authoritative repository</p>
                  <h2 className="mt-1 text-lg font-bold text-slate-950">
                    {location?.repository_name ?? view?.current_repository?.name ?? "Loading..."}
                  </h2>
                  <p className="mt-1 text-sm font-medium text-slate-700">
                    {location?.repository_code ?? view?.current_repository?.code ?? ""} · {location?.jurisdiction ?? view?.current_repository?.jurisdiction ?? ""}
                  </p>
                </div>
                <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-cyan-800">
                  Single repository
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-700">
                HealthNet retrieves this patient's clinical history from this repository only. Other repositories are not searched for this patient.
              </p>
            </div>
          </Card>

          <Card title="Clinical history">
            {records.length === 0 ? (
              <p className="text-sm text-slate-600">No clinical records were returned.</p>
            ) : (
              <div className="space-y-3">
                {records.map((record, index) => <RecordCard key={`${record.resource_type}-${index}`} record={record} />)}
              </div>
            )}
            <div className="mt-5 flex flex-wrap gap-3 text-xs font-semibold text-slate-600">
              <span>{records.length} clinical record{records.length === 1 ? "" : "s"}</span>
              <span>·</span>
              <span>{view?.repositories_checked ?? 1} repository checked</span>
              {view?.completeness && (
                <>
                  <span>·</span>
                  <span>Record status: {view.completeness === "COMPLETE" ? "Complete" : "Partial"}</span>
                </>
              )}
            </div>
            {errors.length > 0 && (
              <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
                <p className="font-bold">Some information could not be loaded.</p>
                <p className="mt-1">The available clinical records are shown above.</p>
              </div>
            )}
          </Card>
        </div>
      )}
    </PortalShell>
  );
}
