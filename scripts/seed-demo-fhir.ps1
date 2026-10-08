# HealthNet local federated FHIR demo
$ErrorActionPreference = "Stop"
$ComposeFile = "infrastructure/docker-compose.yml"
$PostgresContainer = "healthnet-postgres"
$DbUser = "healthnet"
$DemoHealthId = "INOD000038"

function Wait-Postgres {
  for ($i = 0; $i -lt 30; $i++) {
    docker exec $PostgresContainer pg_isready -U $DbUser -d healthnet_db *> $null
    if ($LASTEXITCODE -eq 0) { return }
    Start-Sleep -Seconds 2
  }
  throw "PostgreSQL did not become ready."
}

function Ensure-Database([string]$Name) {
  $exists = docker exec $PostgresContainer psql -U $DbUser -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = ''$Name'';"
  if ($exists.Trim() -ne "1") {
    docker exec $PostgresContainer psql -U $DbUser -d postgres -c "CREATE DATABASE $Name;" | Out-Null
  }
  docker exec $PostgresContainer psql -U $DbUser -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE $Name TO $DbUser;" | Out-Null
}

function Wait-Fhir([string]$BaseUrl, [string]$Name) {
  for ($i = 0; $i -lt 60; $i++) {
    try {
      $response = Invoke-RestMethod -Uri "$BaseUrl/metadata" -Method Get -TimeoutSec 5
      if ($response.resourceType -eq "CapabilityStatement") { Write-Host "$Name FHIR repository is ready: $BaseUrl"; return }
    } catch {}
    Start-Sleep -Seconds 5
  }
  throw "$Name FHIR repository did not become ready."
}

function Put-FhirResource([string]$BaseUrl, [hashtable]$Resource) {
  $json = $Resource | ConvertTo-Json -Depth 30
  Invoke-RestMethod -Uri "$BaseUrl/$($Resource.resourceType)/$($Resource.id)" -Method Put -ContentType "application/fhir+json" -Body $json | Out-Null
}

docker compose -f $ComposeFile up -d postgres | Out-Null
Wait-Postgres
Ensure-Database "hapi_odisha_db"
Ensure-Database "hapi_karnataka_db"
Ensure-Database "hapi_maldives_db"
docker compose -f $ComposeFile up -d | Out-Null
Wait-Fhir "http://localhost:8091/fhir" "Odisha"
Wait-Fhir "http://localhost:8092/fhir" "Karnataka"
Wait-Fhir "http://localhost:8093/fhir" "Maldives"

$patient = @{ resourceType = "Patient"; id = $DemoHealthId; identifier = @(@{ system = "https://healthnet.local/health-id"; value = $DemoHealthId }); name = @(@{ use = "official"; family = "Sharma"; given = @("Aarav") }); gender = "male"; birthDate = "1998-04-12" }
$odishaEncounter = @{ resourceType = "Encounter"; id = "enc-odisha-2024"; status = "finished"; class = @{ system = "http://terminology.hl7.org/CodeSystem/v3-ActCode"; code = "AMB"; display = "ambulatory" }; subject = @{ reference = "Patient/$DemoHealthId" }; period = @{ start = "2024-02-15T10:00:00Z"; end = "2024-02-15T10:30:00Z" }; serviceProvider = @{ display = "Odisha General Hospital" } }
$odishaCondition = @{ resourceType = "Condition"; id = "condition-diabetes-2024"; clinicalStatus = @{ coding = @(@{ system = "http://terminology.hl7.org/CodeSystem/condition-clinical"; code = "active" }) }; verificationStatus = @{ coding = @(@{ system = "http://terminology.hl7.org/CodeSystem/condition-ver-status"; code = "confirmed" }) }; code = @{ coding = @(@{ system = "http://snomed.info/sct"; code = "44054006"; display = "Type 2 diabetes mellitus" }); text = "Type 2 Diabetes" }; subject = @{ reference = "Patient/$DemoHealthId" }; onsetDateTime = "2024-02-15" }
$odishaGlucose = @{ resourceType = "Observation"; id = "glucose-2024"; status = "final"; code = @{ coding = @(@{ system = "http://loinc.org"; code = "2339-0"; display = "Glucose [Mass/volume] in Blood" }); text = "Blood Glucose" }; subject = @{ reference = "Patient/$DemoHealthId" }; effectiveDateTime = "2024-02-15T10:15:00Z"; valueQuantity = @{ value = 168; unit = "mg/dL"; system = "http://unitsofmeasure.org"; code = "mg/dL" } }
$karnatakaEncounter = @{ resourceType = "Encounter"; id = "enc-karnataka-2025"; status = "finished"; class = @{ system = "http://terminology.hl7.org/CodeSystem/v3-ActCode"; code = "AMB"; display = "ambulatory" }; subject = @{ reference = "Patient/$DemoHealthId" }; period = @{ start = "2025-08-20T09:00:00Z"; end = "2025-08-20T09:45:00Z" }; serviceProvider = @{ display = "Bangalore Medical Centre" } }
$karnatakaHba1c = @{ resourceType = "Observation"; id = "hba1c-2025"; status = "final"; code = @{ coding = @(@{ system = "http://loinc.org"; code = "4548-4"; display = "Hemoglobin A1c" }); text = "HbA1c" }; subject = @{ reference = "Patient/$DemoHealthId" }; effectiveDateTime = "2025-08-20T09:15:00Z"; valueQuantity = @{ value = 7.4; unit = "%"; system = "http://unitsofmeasure.org"; code = "%" } }
$karnatakaMedication = @{ resourceType = "MedicationRequest"; id = "metformin-2025"; status = "active"; intent = "order"; medicationCodeableConcept = @{ text = "Metformin" }; subject = @{ reference = "Patient/$DemoHealthId" }; authoredOn = "2025-08-20"; dosageInstruction = @(@{ text = "500 mg twice daily" }) }
$maldivesEncounter = @{ resourceType = "Encounter"; id = "enc-maldives-2026"; status = "finished"; class = @{ system = "http://terminology.hl7.org/CodeSystem/v3-ActCode"; code = "EMER"; display = "emergency" }; subject = @{ reference = "Patient/$DemoHealthId" }; period = @{ start = "2026-03-10T18:00:00Z"; end = "2026-03-10T19:00:00Z" }; serviceProvider = @{ display = "Maldives International Hospital" } }
$maldivesBp = @{ resourceType = "Observation"; id = "blood-pressure-2026"; status = "final"; code = @{ coding = @(@{ system = "http://loinc.org"; code = "85354-9"; display = "Blood pressure panel" }); text = "Blood Pressure" }; subject = @{ reference = "Patient/$DemoHealthId" }; effectiveDateTime = "2026-03-10T18:10:00Z"; component = @(@{ code = @{ text = "Systolic blood pressure" }; valueQuantity = @{ value = 145; unit = "mmHg" } }, @{ code = @{ text = "Diastolic blood pressure" }; valueQuantity = @{ value = 90; unit = "mmHg" } }) }
$maldivesScreening = @{ resourceType = "Observation"; id = "cardiac-screening-2026"; status = "final"; code = @{ text = "Cardiac screening" }; subject = @{ reference = "Patient/$DemoHealthId" }; effectiveDateTime = "2026-03-10T18:30:00Z"; valueString = "Completed" }

Put-FhirResource "http://localhost:8091/fhir" $patient; Put-FhirResource "http://localhost:8091/fhir" $odishaEncounter; Put-FhirResource "http://localhost:8091/fhir" $odishaCondition; Put-FhirResource "http://localhost:8091/fhir" $odishaGlucose
Put-FhirResource "http://localhost:8092/fhir" $patient; Put-FhirResource "http://localhost:8092/fhir" $karnatakaEncounter; Put-FhirResource "http://localhost:8092/fhir" $karnatakaHba1c; Put-FhirResource "http://localhost:8092/fhir" $karnatakaMedication
Put-FhirResource "http://localhost:8093/fhir" $patient; Put-FhirResource "http://localhost:8093/fhir" $maldivesEncounter; Put-FhirResource "http://localhost:8093/fhir" $maldivesBp; Put-FhirResource "http://localhost:8093/fhir" $maldivesScreening

$sql = @"
INSERT INTO healthnet.policy_rule (id, jurisdiction_id, name, purpose, scope, effect, description, active)
SELECT '00000000-0000-0000-0000-000000009001', j.id, 'Demo Odisha treatment access', 'TREATMENT', 'clinical', 'ALLOW', 'Local mentor demo policy', true FROM healthnet.jurisdiction j WHERE j.code = 'IN-OD' AND NOT EXISTS (SELECT 1 FROM healthnet.policy_rule WHERE name = 'Demo Odisha treatment access');
INSERT INTO healthnet.policy_rule (id, jurisdiction_id, name, purpose, scope, effect, description, active)
SELECT '00000000-0000-0000-0000-000000009002', j.id, 'Demo Karnataka treatment access', 'TREATMENT', 'clinical', 'ALLOW', 'Local mentor demo policy', true FROM healthnet.jurisdiction j WHERE j.code = 'IN-KA' AND NOT EXISTS (SELECT 1 FROM healthnet.policy_rule WHERE name = 'Demo Karnataka treatment access');
INSERT INTO healthnet.policy_rule (id, jurisdiction_id, name, purpose, scope, effect, description, active)
SELECT '00000000-0000-0000-0000-000000009003', j.id, 'Demo Maldives treatment access', 'TREATMENT', 'clinical', 'ALLOW', 'Local mentor demo policy', true FROM healthnet.jurisdiction j WHERE j.code = 'MV' AND NOT EXISTS (SELECT 1 FROM healthnet.policy_rule WHERE name = 'Demo Maldives treatment access');
DELETE FROM healthnet.record_locator WHERE health_id = 'INOD000038';
INSERT INTO healthnet.record_locator (id, health_id, repository_id, endpoint, resource_types, status, last_verified_at, notes) VALUES
('00000000-0000-0000-0000-000000009101', 'INOD000038', '00000000-0000-0000-0000-000000000201', 'http://localhost:8091/fhir', 'Patient,Encounter,Condition,Observation', 'ACTIVE', now(), 'Demo Odisha records'),
('00000000-0000-0000-0000-000000009102', 'INOD000038', '00000000-0000-0000-0000-000000000202', 'http://localhost:8092/fhir', 'Patient,Encounter,Observation,MedicationRequest', 'ACTIVE', now(), 'Demo Karnataka records'),
('00000000-0000-0000-0000-000000009103', 'INOD000038', '00000000-0000-0000-0000-000000000203', 'http://localhost:8093/fhir', 'Patient,Encounter,Observation', 'ACTIVE', now(), 'Demo Maldives records');
"@
$sql | docker exec -i $PostgresContainer psql -U $DbUser -d healthnet_db | Out-Null
Write-Host ""
Write-Host "Federated FHIR demo is ready."
Write-Host "Health ID: $DemoHealthId"
Write-Host "Odisha:    http://localhost:8091/fhir"
Write-Host "Karnataka: http://localhost:8092/fhir"
Write-Host "Maldives:  http://localhost:8093/fhir"