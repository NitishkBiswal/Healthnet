# Local Development Guide

This guide describes the current Windows development workflow. For the complete setup including prerequisites, environment values, demo accounts and troubleshooting, see the root [README](../README.md).

## Prerequisites

- Git
- Docker Desktop with Docker Compose v2
- Python 3.11 or newer
- Node.js and npm
- Recommended: at least 8 GB RAM

## 1. Get the current project

```powershell
git clone --branch main https://github.com/NitishkBiswal/Healthnet.git
cd Healthnet
```

For an existing clone:

```powershell
git switch main
git pull origin main
```

## 2. Start infrastructure

Start Docker Desktop, then run from the repository root:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
docker compose -f infrastructure/docker-compose.yml ps
```

The stack includes PostgreSQL, Redis, Keycloak, three HAPI FHIR servers and a one-shot Karnataka database initializer. The initializer is expected to exit after successful completion; it is not a continuously running application service.

## 3. Start the backend

In a second PowerShell window:

```powershell
cd path\to\Healthnet\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Create `backend/.env` using the development settings documented in the root README, then:

```powershell
alembic upgrade head
python -m uvicorn app.main:app --reload
```

## 4. Start the frontend

In a third PowerShell window:

```powershell
cd path\to\Healthnet\frontend
npm install
npm run dev
```

## 5. Open the application

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Keycloak: http://localhost:8180
- Default HAPI FHIR: http://localhost:8090/fhir
- Kolkata HAPI FHIR: http://localhost:8091/fhir
- Karnataka HAPI FHIR: http://localhost:8092/fhir

Keep Docker Desktop and both development terminals running while using the application.

## Stop services safely

Stop containers while preserving persisted data:

```powershell
docker compose -f infrastructure/docker-compose.yml down
```

Do not use `down -v` unless you intentionally want to delete local database/cache volumes and all demo data.

## Verification notes

The root README includes the demo workflow and troubleshooting. Backend test, lint and frontend build commands are documented there. A passing frontend build does not replace manual verification of Keycloak login, portal role checks, patient consent and protected record access.
