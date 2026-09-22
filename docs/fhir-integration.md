# FHIR Integration

## Integration Pattern
FastAPI -> REST -> HAPI FHIR

## Supported FHIR Resources
| Resource | Role |
|---|---|
| Patient | Core identity |
| Practitioner | Provider identity |
| Observation | Clinical findings |
| Condition | Diagnoses |
| ... | ... |

## FastAPI vs HAPI FHIR
FastAPI handles auth, orchestration. HAPI FHIR handles complex search and FHIR storage.

## FHIR Exchange Patterns
- $everything
- $search
- $export/$import
- SMART on FHIR

## Terminology Binding
Planned for future enhancements (SNOMED, ICD, LOINC).
