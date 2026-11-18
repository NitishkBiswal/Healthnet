# Environment Variables Reference

The backend loads settings from `backend/.env` using Pydantic Settings. The values below reflect the current defaults in `backend/app/core/config.py`. Local development values are not production secrets.

## Backend

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `HealthNet` | API application name |
| `APP_VERSION` | `0.1.0` | API version metadata |
| `DEBUG` | `false` | Debug setting |
| `API_V1_PREFIX` | `/api/v1` | Prefix for versioned API routers |
| `DATABASE_URL` | `postgresql+asyncpg://healthnet:healthnet_dev_password@localhost:5432/healthnet_db` | Async HealthNet database connection |
| `DATABASE_SYNC_URL` | `postgresql+psycopg2://healthnet:healthnet_dev_password@localhost:5432/healthnet_db` | Synchronous database connection used by tooling |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `KEYCLOAK_URL` | `http://localhost:8180` | Keycloak base URL |
| `KEYCLOAK_REALM` | `healthnet` | Keycloak realm |
| `KEYCLOAK_CLIENT_ID` | `healthnet-backend` | Backend Keycloak client ID |
| `KEYCLOAK_CLIENT_SECRET` | development default in config | Backend client secret; keep private |
| `KEYCLOAK_ADMIN_USERNAME` | `admin` | Local Keycloak admin username |
| `KEYCLOAK_ADMIN_PASSWORD` | `admin` | Local Keycloak admin password |
| `HAPI_FHIR_BASE_URL` | `http://localhost:8090/fhir` | Default HAPI FHIR base URL |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed browser origins |
| `SECRET_KEY` | development placeholder in config | Application signing/encryption fallback; replace outside local demo |
| `AADHAAR_ENCRYPTION_KEY` | empty | Dedicated key for Aadhaar encryption; configure securely if the feature is used |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Application access-token expiry setting |

The Compose credentials and defaults are intended only for a local demo. Do not expose them to the public internet or reuse them in a deployed environment.

## Frontend

The frontend reads these public build/runtime environment variables and also has local defaults in its authentication/API code:

| Variable | Local default / example | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | FastAPI base URL |
| `NEXT_PUBLIC_KEYCLOAK_URL` | `http://localhost:8180` | Keycloak base URL |
| `NEXT_PUBLIC_KEYCLOAK_REALM` | `healthnet` | Keycloak realm |
| `NEXT_PUBLIC_KEYCLOAK_CLIENT_ID` | `healthnet-frontend` | Public frontend OIDC client |

Create `backend/.env` and `frontend/.env.local` locally as needed. Never commit either file, access tokens, encryption keys or real patient information.
