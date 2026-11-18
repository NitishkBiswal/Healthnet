# API Documentation

## Interactive API reference

When the backend is running:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

The FastAPI application mounts the versioned application and health routers under the configured API prefix, which defaults to `/api/v1`. The root endpoint at `http://localhost:8000/` returns basic application metadata and the docs path.

## Authentication

Protected application endpoints use Keycloak-issued bearer access tokens. The frontend starts the OpenID Connect Authorization Code flow with PKCE and checks the selected portal role after login. API requests must carry a valid `Authorization: Bearer <token>` header where authentication is required.

Do not disable authentication to work around an unauthorized response. Verify the Keycloak realm/client configuration, account role and request token instead.

## Endpoint reference

The live OpenAPI document at `/openapi.json` is the authoritative list of routes, request/response schemas and security requirements. Use Swagger UI to inspect the current route groups, including identity, provider, consent, authorization, longitudinal records, repository, medical import, audit and FHIR-related workflows that are registered in this checkout.

## Error handling and tracing

The API uses structured FastAPI/Pydantic error responses. Do not assume every error is RFC 7807 unless the specific endpoint schema documents that format. Where supported, the backend uses structured logging for troubleshooting. Consult the live OpenAPI schema and backend implementation when integrating a client.
