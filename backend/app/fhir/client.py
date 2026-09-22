"""
HAPI FHIR integration client.

FastAPI communicates with HAPI FHIR server via REST API.
This module does NOT reimplement a FHIR server — it is an HTTP client
to the HAPI FHIR server that handles all FHIR R4 resource storage and search.

MVP IMPLEMENTATION: Basic HTTP client stubs. Full integration in Segment 7.
"""

from typing import Any

import httpx

from app.core.config import settings


class FHIRClient:
    """HTTP client for communicating with the HAPI FHIR R4 server."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.HAPI_FHIR_BASE_URL

    async def get_metadata(self) -> dict[str, Any]:
        """GET /metadata — retrieve FHIR CapabilityStatement."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/metadata", timeout=5.0)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

    async def get_resource(self, resource_type: str, resource_id: str) -> dict[str, Any]:
        """GET /{resourceType}/{id} — retrieve a single FHIR resource."""
        # TODO: Implement in Segment 7
        raise NotImplementedError("FHIR resource retrieval — Segment 7")

    async def search(self, resource_type: str, params: dict[str, Any]) -> dict[str, Any]:
        """GET /{resourceType}?params — search FHIR resources."""
        # TODO: Implement in Segment 7
        raise NotImplementedError("FHIR resource search — Segment 7")

    async def create_resource(self, resource_type: str, resource: dict[str, Any]) -> dict[str, Any]:
        """POST /{resourceType} — create a FHIR resource."""
        # TODO: Implement in Segment 7
        raise NotImplementedError("FHIR resource creation — Segment 7")

    async def health_check(self) -> bool:
        """Check if HAPI FHIR server is reachable."""
        try:
            await self.get_metadata()
            return True
        except Exception:
            return False
