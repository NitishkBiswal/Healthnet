"use client";

import Link from "next/link";
import { useState } from "react";

import { Card, Field, PortalShell } from "@/components/portal-shell";
import { api } from "@/lib/api";

type RecordType = "Observation" | "Encounter" | "Condition";

export default function HospitalIntegrationDemo() {
  const [healthId, setHealthId] = useState("");
  const [recordType, setRecordType] = useState<RecordType>("Observation");
  const [label, setLabel] = useState("Blood pressure");
  const [value, setValue] = useState("128");
  const [unit, setUnit] = useState("mmHg");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.submitPatientRecord>> | null>(null);

  async function submitRecord() {
    setError("");
    setResult(null);
    if (!healthId.trim()) {
      setError("Enter the patient's Health ID.");
      return;
    }

    const now = new Date().toISOString();
    let resource: Record<string, unknown>;
    if (recordType === "Observation") {
      const numericValue = Number(value);
      if (!Number.isFinite(numericValue)) {
        setError("Enter a valid numeric observation value.");
        return;
      }
      resource = {
        resourceType: "Observation",
        status: "final",
        code: { text: label.trim() || "Clinical observation" },
        subject: { reference: `Patient/${healthId.trim()}` },
        effectiveDateTime: now,
        valueQuantity: {
          value: numericValue,
          unit: unit.trim() || "units",
          system: "http://unitsofmeasure.org",
          code: unit.trim() === "mmHg" ? "mm[Hg]" : unit.trim() || "1",
        },
      };
    } else if (recordType === "Encounter") {
      resource = {
        resourceType: "Encounter",
        status: "finished",
        class: {
          system: "http://terminology.hl7.org/CodeSystem/v3-ActCode",
          code: "AMB",
          display: "ambulatory",
        },
        type: [{ text: label.trim() || "Hospital visit" }],
        subject: { reference: `Patient/${healthId.trim()}` },
        period: { start: now },
      };
    } else {
      resource = {
        resourceType: "Condition",
        clinicalStatus: { coding: [{ system: "http://terminology.hl7.org/CodeSystem/condition-clinical", code: "active" }] },
        verificationStatus: { coding: [{ system: "http://terminology.hl7.org/CodeSystem/condition-ver-status", code: "confirmed" }] },
        code: { text: label.trim() || "Recorded condition" },
        subject: { reference: `Patient/${healthId.trim()}` },
        recordedDate: now.slice(0, 10),
      };
    }

    setBusy(true);
    try {
      setResult(await api.submitPatientRecord(healthId.trim(), resource));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Record submission failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PortalShell
      requiredRole="provider"
      title="Hospital Integration Demo"
      description="Simulate a trusted hospital sending a FHIR clinical record. HealthNet resolves the patient's current repository automatically."
    >
      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Submit a clinical record">
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-semibold text-slate-900">Patient Health ID</label>
              <Field value={healthId} onChange={(event) => setHealthId(event.target.value)} placeholder="e.g. INOD000100" autoCapitalize="characters" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-semibold text-slate-900">FHIR record type</label>
              <select value={recordType} onChange={(event) => setRecordType(event.target.value as RecordType)} className="w-full rounded-lg border-2 border-slate-400 bg-white px-3 py-2 text-sm font-medium text-slate-950">
                <option value="Observation">Observation — measurement or test result</option>
                <option value="Encounter">Encounter — hospital visit</option>
                <option value="Condition">Condition — diagnosis or health condition</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-semibold text-slate-900">{recordType === "Observation" ? "Observation name" : recordType === "Encounter" ? "Visit description" : "Condition description"}</label>
              <Field value={label} onChange={(event) => setLabel(event.target.value)} placeholder="e.g. Blood pressure" />
            </div>
            {recordType === "Observation" && (
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-900">Measured value</label>
                  <Field type="number" value={value} onChange={(event) => setValue(event.target.value)} />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-semibold text-slate-900">Unit</label>
                  <Field value={unit} onChange={(event) => setUnit(event.target.value)} placeholder="mmHg, mg/dL, etc." />
                </div>
              </div>
            )}
            <button disabled={busy} onClick={submitRecord} className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-50">
              {busy ? "Submitting record…" : "Send record to HealthNet"}
            </button>
            {error && <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-800">{error}</p>}
            {result && (
              <div role="status" className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-950">
                <p className="font-bold">Record accepted</p>
                <p className="mt-1">Health ID: {result.health_id}</p>
                <p>Repository: {result.repository_code}</p>
                <p>Record: {result.resource_type}/{result.resource_id}</p>
                <p className="mt-1">{result.message}</p>
              </div>
            )}
          </div>
        </Card>

        <Card title="What this demo verifies">
          <ol className="list-decimal space-y-3 pl-5 text-sm text-slate-700">
            <li>The caller is signed in and linked to an active trusted HealthNet provider record.</li>
            <li>HealthNet resolves the patient's active repository from the Record Locator; the sender cannot choose an endpoint.</li>
            <li>The patient Health ID and FHIR patient reference are validated before the record is written.</li>
            <li>The record is stored using an idempotent FHIR PUT and the repository's resource-type list is updated.</li>
            <li>After a verified repository migration, subsequent submissions follow the new active assignment.</li>
          </ol>
          <p className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950">
            Semester-project simulation: this page uses a trusted provider login as the hospital sender. A production deployment should use separately registered hospital/service identities, transport security, and stronger provenance controls.
          </p>
          <Link href="/doctor" className="mt-4 inline-block text-sm font-bold text-cyan-800 underline">Return to Doctor Portal</Link>
        </Card>
      </div>
    </PortalShell>
  );
}
