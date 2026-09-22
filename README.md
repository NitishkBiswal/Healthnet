# HealthNet — Global Federated Health Identity & Interoperability Network

> "Building a unified, global healthcare identity."

HealthNet is a Global Federated Health Identity & Interoperability Network designed to securely connect disparate healthcare systems. It provides identity management, secure interoperability, and data harmonization.

## Architecture

```text
[Frontend (Next.js)] <-> [Backend (FastAPI)] <-> [Database (PostgreSQL)]
                               |-> [Auth (Keycloak)]
                               |-> [Cache (Redis)]
                               |-> [FHIR (HAPI FHIR)]
```

## Tech Stack
| Component | Technology |
|---|---|
| Backend | Python 3.11.4, FastAPI |
| Frontend | Next.js |
| Database | PostgreSQL |
| Cache | Redis |
| Auth | Keycloak |
| FHIR Server | HAPI FHIR |
| Containerization | Docker |

## Quick Start

1. Clone repository
2. Run docker-compose up
```bash
docker-compose -f infrastructure/docker-compose.yml up -d
```
3. Start Backend
```bash
uvicorn app.main:app --reload
```
4. Start Frontend
```bash
npm run dev
```

## Modules
1. Foundation
... (and 17 more, implementing various capabilities)

## Project Structure
```text
/backend
/frontend
/infrastructure
/docs
/tests
```

## Development
Run tests using `pytest`. Lint with `ruff`.

## Roadmaps
Segments 0-17

## Documentation
See `docs/` folder.

## License
MIT
