$ErrorActionPreference = "Stop"
$healthId = "INOD000038"
$repos = @(
  @{ Name = "Odisha"; Url = "http://localhost:8091/fhir" },
  @{ Name = "Karnataka"; Url = "http://localhost:8092/fhir" },
  @{ Name = "Maldives"; Url = "http://localhost:8093/fhir" }
)
foreach ($repo in $repos) {
  $bundle = Invoke-RestMethod "$($repo.Url)/Observation?patient=$healthId"
  $count = @($bundle.entry).Count
  Write-Host ("{0,-12} OK  Observations: {1}" -f $repo.Name, $count)
}
Write-Host ""
Write-Host "Docker repositories:"
docker compose -f infrastructure/docker-compose.yml ps hapi-fhir-odisha hapi-fhir-karnataka hapi-fhir-maldives