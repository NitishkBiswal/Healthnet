# HealthNet Frontend

This directory contains the Next.js frontend for the HealthNet patient, provider, administrator and auditor portals.

## Run locally

From this directory:

```bash
npm install
npm run dev
```

Open http://localhost:3000. The frontend expects the FastAPI backend at http://localhost:8000 and Keycloak at http://localhost:8180 by default.

## Available scripts

- `npm run dev` — start the development server.
- `npm run build` — create a production build.
- `npm run start` — serve a production build.
- `npm run lint` — run ESLint.

## Authentication and theme

Authentication uses Keycloak with OpenID Connect Authorization Code flow and PKCE. The role-specific sign-in pages redirect to the HealthNet realm; the Keycloak login screen is styled with the custom theme in `../infrastructure/keycloak/themes/healthnet`. The theme is mounted by the Docker Compose configuration. It changes presentation, not the underlying Keycloak authentication flow.

## Full setup

See the repository [README](../README.md) for the complete Windows setup, Docker infrastructure, backend configuration, demo accounts and troubleshooting.
