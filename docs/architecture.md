# Architecture

## Core Design Principle
Modularity and scalability via separation of concerns.

## Five Separations
| Separation | Description |
|---|---|
| Domain | Separation by business capability |
| Component | Clear component boundaries |
| Data | Dedicated datastores per service |
| Execution | Async execution where necessary |
| Interface | Clear API contracts |

## Component Responsibility Matrix
- **API Gateway**: Routing, rate limiting (Never does business logic)
- **Identity Provider**: Authentication (Never holds clinical data)
- **Clinical Repository**: FHIR data storage (Never does auth)
- **...**

## System Boundary Diagram
```text
[External Clients] -> [API Gateway] -> [Services] -> [Databases]
```

## Module Dependency Rules
No cross-module imports allowed.

## HAPI FHIR Integration Boundary
Backend delegates FHIR-specific complex queries to HAPI FHIR.

## Data Flow
- Retrieval: API -> DB/FHIR -> API -> Client
- Migration: Legacy -> Transform -> FHIR -> Client
