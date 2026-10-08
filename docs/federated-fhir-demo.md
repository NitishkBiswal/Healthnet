# HealthNet Federated FHIR Demo

This demo runs three independent HAPI FHIR repositories locally.

| Repository | Jurisdiction | Endpoint | Database |
|---|---|---|---|
| Odisha Health Repository | IN-OD | http://localhost:8091/fhir | hapi_odisha_db |
| Karnataka Health Repository | IN-KA | http://localhost:8092/fhir | hapi_karnataka_db |
| Maldives Health Repository | MV | http://localhost:8093/fhir | hapi_maldives_db |

HealthNet PostgreSQL stores repository and Record Locator metadata. Clinical FHIR resources remain in the jurisdictional repositories.

## One-command setup

From the repository root in PowerShell:

```powershell
.\scripts\seed-demo-fhir.ps1
```

The script starts PostgreSQL, creates missing FHIR databases, starts the three repositories, waits for them, seeds Health ID `INOD000038`, registers Record Locators, and adds local cross-jurisdiction treatment/clinical policy rules. It is repeatable.

## Demo patient

**INOD000038 — Aarav Sharma**

- **2024 / Odisha General Hospital:** consultation, Type 2 Diabetes, blood glucose 168 mg/dL.
- **2025 / Bangalore Medical Centre:** follow-up, HbA1c 7.4%, Metformin.
- **2026 / Maldives International Hospital:** emergency consultation, blood pressure 145/90, cardiac screening completed.

## Mentor demo

1. Run `scripts\seed-demo-fhir.ps1`.
2. Start the backend with `cd backend`, `\.venv\Scripts\Activate.ps1`, then `uvicorn app.main:app --reload`.
3. Start the frontend with `cd frontend` then `npm run dev`.
4. Log in as `testpatient / patient`.
5. If the doctor account is not already linked to a HealthNet Provider, use the Admin portal to onboard a doctor first. The onboarding flow creates the Keycloak account and Provider ID.
6. Confirm Health ID `INOD000038` and grant the doctor's Provider ID access for `TREATMENT` + `clinical`.
7. Log in as the doctor, select the authorized patient, and request the longitudinal view.
8. Explain that HealthNet used the Record Locator to query three independent FHIR repositories at request time; clinical records are not centralized.

## Verify federation directly

```powershell
Invoke-RestMethod "http://localhost:8091/fhir/Observation?patient=INOD000038"
Invoke-RestMethod "http://localhost:8092/fhir/Observation?patient=INOD000038"
Invoke-RestMethod "http://localhost:8093/fhir/Observation?patient=INOD000038"
```

Before the UI demo, you can verify all three repositories with `scripts\verify-demo-fhir.ps1`.

To demonstrate partial availability:

```powershell
docker stop healthnet-hapi-fhir-odisha
```

Request the longitudinal view again. It should report two available repositories and `PARTIAL` completeness while still returning records from the available repositories. Restore with `docker start healthnet-hapi-fhir-odisha` and request again for `COMPLETE`.

## Architecture

```text
Patient → Health ID → Consent + Provider Trust + Jurisdiction Policy
                         ↓
                    Record Locator
                         ↓
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
       Odisha        Karnataka       Maldives
       HAPI FHIR     HAPI FHIR       HAPI FHIR
          └──────────────┼──────────────┘
                         ↓
              Federated Longitudinal View
```