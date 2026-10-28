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

1. Start PostgreSQL, Redis, Keycloak, and HAPI FHIR:
```bash
docker compose -f infrastructure/docker-compose.yml up -d
```
2. Install backend dependencies and apply the database migrations:
```bash
cd backend
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
   Run migrations only after PostgreSQL is healthy and keep the migration environment's database credentials secret.
3. In a second terminal, start the frontend:
```bash
cd frontend
npm install
npm run dev
```
4. Open `http://localhost:3000`. The development Keycloak issuer is `http://localhost:8180/realms/healthnet`.
   Production deployments must set `ENVIRONMENT=production` and supply non-default database, Keycloak, and application secrets.

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
