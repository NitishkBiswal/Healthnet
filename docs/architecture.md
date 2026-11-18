# HealthNet Architecture

## Overview

HealthNet is a local development and academic demonstration prototype for federated healthcare identity, consent-controlled record access and FHIR interoperability. It is not a production deployment or a certified ABDM integration.

## Runtime components

| Component | Responsibility | Local endpoint |
|---|---|---|
| Next.js frontend | Patient, provider, administrator and auditor user interfaces | http://localhost:3000 |
| FastAPI backend | API, authentication/authorization checks, consent and workflow orchestration | http://localhost:8000 |
| PostgreSQL | HealthNet application data and separate Keycloak/HAPI databases | localhost:5432 |
| Redis | Application cache / supporting transient data | localhost:6379 |
| Keycloak 25 | OpenID Connect identity provider, realm roles and login/registration | http://localhost:8180 |
| HAPI FHIR R4 — default | Default jurisdictional clinical repository | http://localhost:8090/fhir |
| HAPI FHIR R4 — Kolkata | Kolkata demonstration repository | http://localhost:8091/fhir |
| HAPI FHIR R4 — Karnataka | Karnataka demonstration repository | http://localhost:8092/fhir |

The infrastructure is defined in `infrastructure/docker-compose.yml`. In the documented local-development workflow, Docker runs the supporting services while FastAPI and Next.js run directly on the host.

## Main request paths

- **Authentication:** Browser -> Keycloak using OpenID Connect Authorization Code flow with PKCE -> frontend callback -> API requests with bearer access token.
- **Patient consent:** Patient Portal -> FastAPI consent endpoints -> PostgreSQL. Provider access is checked by the backend before protected clinical records are returned.
- **Clinical records:** Frontend -> FastAPI -> active repository locator / HAPI FHIR endpoint. Clinical payloads are stored in HAPI FHIR repositories rather than being treated as ordinary frontend data.
- **Audit and administration:** Administrative/provider/auditor actions pass through role-protected backend workflows and are recorded where the corresponding audit functionality is implemented.
- **Repository transfer demonstration:** The application coordinates FHIR resource export/import between the configured HAPI repositories, reads destination resources back and verifies the transfer package before changing the active locator.

## Data boundaries

- PostgreSQL stores HealthNet application metadata such as identities, provider information, consent and repository-locator/custody information.
- Keycloak stores authentication identities and realm configuration in its own database.
- Each HAPI FHIR instance uses a separate PostgreSQL database for its FHIR repository.
- Redis is used for cache/supporting transient operations; it is not the authoritative clinical record store.

## Identity, consent and trust

HealthNet's internal Health ID is distinct from external government identifiers such as Aadhaar or ABHA. The prototype's Health ID must not be described as an ABHA number. Keycloak authenticates users; the backend enforces application role and consent checks. A patient grant can be revoked, after which subsequent protected access requests should no longer be authorized.

## User interface

The landing page, portal selection/sign-in pages and Keycloak login theme share a light slate background, white surfaces and blue accents. The Keycloak theme is mounted read-only into the Keycloak container from `infrastructure/keycloak/themes/healthnet`. Theme styling does not replace Keycloak's authentication implementation.

## Local URLs

See the root [README](../README.md) for prerequisites, environment configuration, start/stop commands, demo accounts and troubleshooting.
