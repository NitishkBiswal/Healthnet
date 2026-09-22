# API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Versioning
Use `/api/v1/` prefix.

## Error Response
Follows RFC 7807 (Problem Details).

## Correlation ID
Pass `X-Correlation-ID` header.

## Authentication
OAuth2 Bearer token (Keycloak).

## Endpoints (Segment 0)
- `GET /health`
- `GET /health/db`
