# HealthNet — Global Federated Health Identity & Interoperability Network

HealthNet is a development prototype for federated healthcare identity and interoperability. It connects a Next.js web application and FastAPI API to PostgreSQL, Redis, Keycloak, and jurisdiction-specific HAPI FHIR servers.

> **Development/demo software only.** Do not use real patient data, production credentials, or expose these services to the public internet. The credentials in the Docker Compose configuration and demo seed script are intentionally for local development.

## Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [New PC setup (Windows)](#new-pc-setup-windows)
- [Start and stop the services](#start-and-stop-the-services)
- [Open the application](#open-the-application)
- [Demo accounts and sample records](#demo-accounts-and-sample-records)
- [Typical demo workflow](#typical-demo-workflow)
- [Useful commands](#useful-commands)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)

## Architecture

The current Compose file starts the supporting infrastructure in Docker. The API and web frontend are run as development processes on the host machine.

| Component | Technology | Local URL / port |
|---|---|---|
| Web frontend | Next.js | http://localhost:3000 |
| API | FastAPI / Uvicorn | http://localhost:8000 |
| API docs | FastAPI Swagger UI | http://localhost:8000/docs |
| Database | PostgreSQL 16 | localhost:5432 |
| Cache | Redis 7 | localhost:6379 |
| Identity provider | Keycloak 25 | http://localhost:8180 |
| HAPI FHIR (default) | HAPI FHIR R4 | http://localhost:8090/fhir |
| HAPI FHIR (Kolkata) | HAPI FHIR R4 | http://localhost:8091/fhir |
| HAPI FHIR (Karnataka) | HAPI FHIR R4 | http://localhost:8092/fhir |

The Compose stack is defined in `infrastructure/docker-compose.yml`. It includes PostgreSQL, Redis, Keycloak, and three HAPI FHIR instances (default/Odisha, Kolkata and Karnataka). PostgreSQL hosts separate databases for the application, Keycloak and each FHIR instance. The `karnataka-db-init` one-shot container creates the Karnataka FHIR database when needed and exits after successful initialization. The Keycloak service mounts the custom HealthNet login theme from `infrastructure/keycloak/themes/healthnet`.

## Current project status

The current `main` branch contains the working HealthNet classroom/demo prototype and the unified light user interface. The public landing page, role-selection pages, and Keycloak sign-in theme use the same light slate, white-card and blue-accent design. Keycloak retains its native OpenID Connect login, registration and password-reset flows; the custom theme changes presentation only.

The local demonstration includes patient, provider, administrator and auditor portals; patient consent grant/revocation; provider access to authorized patient records; administrative provider/repository workflows; CSV/Excel medical-record import; audit views; and multi-repository HAPI FHIR demonstration infrastructure. Feature availability should be checked in the running application and API docs; this README is not a claim of production readiness or regulatory certification.

## Prerequisites

Install these on a new development PC:

1. **Git** — to clone the repository.
2. **Docker Desktop** — use the WSL 2 backend on Windows and ensure Docker Desktop is running.
3. **Python 3.11 or newer** — the backend requires Python >=3.11.
4. **Node.js and npm** — use a current supported Node.js LTS release.
5. **At least 8 GB RAM recommended** — HAPI FHIR and Keycloak are resource-intensive; more memory is helpful.

Check installations in PowerShell:

```powershell
git --version
docker --version
docker compose version
python --version
node --version
npm --version
```

## New PC setup (Windows)

### 1. Clone the repository

Open PowerShell:

```powershell
git clone --branch main https://github.com/NitishkBiswal/Healthnet.git
cd Healthnet
```

If you already have a clone, switch to the project branch and pull the latest changes:

```powershell
git switch main
git pull
```

### 2. Start infrastructure with Docker

Make sure Docker Desktop is running, then from the repository root:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

The first start downloads several large images and may take a while. Check container status:

```powershell
docker compose -f infrastructure/docker-compose.yml ps
```

Wait for PostgreSQL and the services to initialize. Keycloak and HAPI FHIR can take a few minutes on first startup. Keycloak imports the realm from `infrastructure/keycloak/healthnet-realm.json`; the bootstrap container configures local demo-user defaults.

### 3. Configure and start the backend

Open a **second PowerShell window**:

```powershell
cd path\to\Healthnet\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

If PowerShell blocks activation, run this once for the current terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Create `backend/.env` (this file is local and must not be committed) with the following development configuration:

```dotenv
APP_NAME=HealthNet
APP_VERSION=0.1.0
DEBUG=true
DATABASE_URL=postgresql+asyncpg://healthnet:healthnet_dev_password@localhost:5432/healthnet_db
DATABASE_SYNC_URL=postgresql+psycopg2://healthnet:healthnet_dev_password@localhost:5432/healthnet_db
REDIS_URL=redis://localhost:6379/0
KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_REALM=healthnet
KEYCLOAK_CLIENT_ID=healthnet-backend
KEYCLOAK_CLIENT_SECRET=healthnet-backend-secret
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=admin
HAPI_FHIR_BASE_URL=http://localhost:8090/fhir
SECRET_KEY=local-development-only-change-this
CORS_ORIGINS=["http://localhost:3000"]
```

Apply the database migrations from the `backend` directory:

```powershell
alembic upgrade head
```

Then start the API:

```powershell
python -m uvicorn app.main:app --reload
```

Keep this terminal open. The API should be available at http://localhost:8000 and the interactive API documentation at http://localhost:8000/docs.

### 4. Install and start the frontend

Open a **third PowerShell window**:

```powershell
cd path\to\Healthnet\frontend
npm install
npm run dev
```

The frontend defaults to the local API at `http://localhost:8000/api/v1` and Keycloak at `http://localhost:8180`. If you need to override these values, create `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_KEYCLOAK_URL=http://localhost:8180
NEXT_PUBLIC_KEYCLOAK_REALM=healthnet
NEXT_PUBLIC_KEYCLOAK_CLIENT_ID=healthnet-frontend
```

Open http://localhost:3000.

### 5. Confirm the services are ready

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs
- Keycloak admin console: http://localhost:8180 (local admin credentials: `admin` / `admin`)
- HAPI FHIR metadata: http://localhost:8090/fhir/metadata

The Keycloak realm is named `healthnet`. The frontend is configured to use the public `healthnet-frontend` client; the API validates tokens for the `healthnet` realm.

## Start and stop the services

Start the infrastructure from the repository root:

```powershell
docker compose -f infrastructure/docker-compose.yml up -d
```

Stop containers but preserve database/cache volumes:

```powershell
docker compose -f infrastructure/docker-compose.yml down
```

Stop containers **and delete all persisted local database/cache data** (destructive):

```powershell
docker compose -f infrastructure/docker-compose.yml down -v
```

To follow logs:

```powershell
docker compose -f infrastructure/docker-compose.yml logs -f
docker compose -f infrastructure/docker-compose.yml logs -f postgres keycloak
```

Do not run `down -v` if you need to keep your local demo users, identities, consents, or FHIR records.

## Open the application

Go to http://localhost:3000 and choose the relevant portal:

- **Patient** — manage patient profile, view medical records, grant/revoke provider consent, and view repository information.
- **Doctor / Provider** — view the HealthNet Provider ID and patients who have granted access; open a patient's longitudinal record only when authorized.
- **Administrator** — manage provider registry and use administrative functions such as medical-record import.
- **Auditor** — access audit and integrity review features.

Authentication is handled by Keycloak. Use the portal matching the role assigned to the account.

## Demo accounts and sample records

The realm import includes local test accounts:

| Username | Role | Password |
|---|---|---|
| `testadmin` | Administrator | `admin` |
| `testdoctor` | Provider | `doctor` |
| `testpatient` | Patient | `patient` |
| `testauditor` | Auditor | `auditor` |

These are only basic Keycloak test identities. The project also has a separate seed script for four linked patient identities and an import CSV. Run it only after the database migrations and the jurisdiction repositories have been configured and are online.

From the `backend` directory with the virtual environment active:

```powershell
python -m scripts.seed_demo_patients
```

The script creates/updates these local demo patient accounts with the password `PatientDemo!2026` and writes `frontend/public/demo-medical-records.csv`:

| Username | Demo patient | Jurisdiction |
|---|---|---|
| `testpatient1` | Aditi Rao | `IN-KA` |
| `testpatient2` | Rohan Kulkarni | `IN-KA` |
| `testpatient3` | Ananya Das | `IN-OD` |
| `testpatient4` | Arjun Mohanty | `IN-OD` |

After seeding, sign in to the Admin Portal, open **Medical Records Import**, and upload `frontend/public/demo-medical-records.csv`.

> Demo passwords and records are public development fixtures. Never reuse them outside a local demo environment.

## Typical demo workflow

1. Sign in to the Admin Portal and confirm the provider/repository setup.
2. Register a provider in **Provider Registry**. Save the generated HealthNet Provider ID.
3. Sign in as a seeded patient, for example `testpatient1`.
4. Open **Grant & revoke consents**, enter the provider's HealthNet Provider ID, choose purpose `TREATMENT` and scope `clinical`, then grant consent.
5. Sign out and sign in to the Doctor Portal using that provider account.
6. Confirm the patient appears in **Patients who have granted you access** and open the longitudinal record.
7. Sign in as the patient again and revoke the consent. Verify that the provider can no longer access the patient's record.

Use the HealthNet Provider ID generated by Provider Registry for consent. Do not use the doctor's username or Keycloak subject as the consent grantee ID.

## Useful commands

Run these from the appropriate directory.

**Backend (from `backend/`):**

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Apply latest migrations
alembic upgrade head

# Run API
python -m uvicorn app.main:app --reload

# Run tests
pytest

# Lint
ruff check .
```

**Frontend (from `frontend/`):**

```powershell
npm install
npm run dev
npm run lint
npm run build
```

## Troubleshooting

### Docker containers are not running

Check Docker Desktop, then:

```powershell
docker compose -f infrastructure/docker-compose.yml ps
docker compose -f infrastructure/docker-compose.yml logs --tail 100
```

### Keycloak login redirects or fails

- Wait until the Keycloak container has finished starting and the `healthnet` realm is imported.
- Confirm the frontend uses `http://localhost:8180`, realm `healthnet`, and client `healthnet-frontend`.
- Use the correct portal and an account with the corresponding realm role.
- If you changed ports or hostnames, update the Keycloak client redirect URI/web origins and the frontend environment values consistently.
- For stale local browser sessions, sign out and retry in a private/incognito window.

### API returns 401 Unauthorized

The API requires a valid Keycloak access token. Confirm that Keycloak is reachable, the account has the expected realm role, and the browser request includes an Authorization Bearer token. Do not disable API authentication to work around a 401.

### API cannot connect to PostgreSQL or Redis

When the backend runs on the host, use `localhost` in `backend/.env`. The Docker service names such as `postgres` and `redis` resolve only from containers on the Compose network.

### FHIR service is slow on first start

HAPI FHIR may need several minutes to initialize its database and metadata endpoint. Check its logs:

```powershell
docker compose -f infrastructure/docker-compose.yml logs -f hapi-fhir hapi-fhir-kolkata hapi-fhir-karnataka
```

### Port already in use

Ensure ports 3000, 5432, 6379, 8000, 8090, 8091, 8092, and 8180 are available, or update the relevant service and application configuration consistently.

## Project structure

```text
Healthnet/
├── backend/                 # FastAPI application, Alembic migrations, scripts
├── frontend/                # Next.js application
├── infrastructure/
│   ├── docker-compose.yml   # PostgreSQL, Redis, Keycloak, HAPI FHIR
│   ├── init-databases.sql
│   └── keycloak/            # Realm import and local bootstrap
├── docs/                    # Project documentation
└── README.md
```

## Development notes

- This README describes the current local-development workflow: infrastructure in Docker; backend and frontend run on the host.
- The Compose file uses development credentials and the HAPI FHIR `latest` image. Pin and secure images/secrets before any shared or production deployment.
- Never commit `.env`, `backend/.env`, `frontend/.env.local`, access tokens, private keys, or real patient information.
- Database migrations are managed with Alembic. Run `alembic upgrade head` after pulling schema changes.
