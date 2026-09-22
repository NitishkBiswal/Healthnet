# Coding Standards

- **Python**: Ruff for lint/format, type hints everywhere, docstrings on public API, Pydantic, SQLAlchemy 2.0 style.
- **TypeScript**: Strict mode, ESLint, Tailwind.
- **Naming**: `snake_case` for Python, `camelCase` for TypeScript, `PascalCase` for classes.
- **Error Handling**: RFC 7807 structured errors. Never swallow exceptions.
- **Logging**: `structlog`, correlation IDs, NO PII.
- **Testing**: `pytest` (backend), `Vitest`/`Jest` (frontend), `Playwright` (E2E).
- **Git**: Conventional commits, feature branches, PR reviews.
- **Security**: No hardcoded secrets, validate all inputs.
