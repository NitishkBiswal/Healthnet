import json
from typing import Any

import httpx

from app.core.config import settings


class FHIRClientError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        message: str,
        operation_outcome: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.operation_outcome = operation_outcome


class FHIRClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.HAPI_FHIR_BASE_URL).rstrip("/")

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        try:
            target = (
                path
                if path.startswith(self.base_url + "/")
                else f"{self.base_url}/{path.lstrip('/')}"
            )
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(method, target, **kwargs)
        except httpx.HTTPError as exc:
            raise FHIRClientError(502, "FHIR repository is unavailable") from exc
        try:
            body = response.json()
        except ValueError:
            body = None
        if response.is_error:
            outcome = body if isinstance(body, dict) and body.get("resourceType") == "OperationOutcome" else None
            issues = outcome.get("issue", []) if outcome else []
            details = [
                issue.get("diagnostics")
                or issue.get("details", {}).get("text")
                or issue.get("code")
                for issue in issues
                if isinstance(issue, dict)
            ]
            message = "; ".join(str(detail) for detail in details if detail)
            if not message:
                message = response.reason_phrase or "FHIR repository request failed"
            raise FHIRClientError(response.status_code, message, outcome)
        if isinstance(body, dict):
            return body
        return {}

    async def get_metadata(self) -> dict[str, Any]:
        return await self._request("GET", "metadata")

    async def get_resource(
        self, resource_type: str, resource_id: str
    ) -> dict[str, Any]:
        return await self._request("GET", f"{resource_type}/{resource_id}")

    async def search(
        self, resource_type: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request("GET", resource_type, params=params)

    async def create_resource(
        self, resource_type: str, resource: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            resource_type,
            json=resource,
            headers={"Content-Type": "application/fhir+json"},
        )

    async def update_resource(
        self, resource_type: str, resource_id: str, resource: dict[str, Any]
    ) -> dict[str, Any]:
        if resource.get("resourceType") != resource_type:
            raise ValueError("FHIR resourceType must match the requested resource type")
        if resource.get("id") not in {None, resource_id}:
            raise ValueError("FHIR resource id must match the requested resource id")
        payload = {**resource, "id": resource_id}
        return await self._request(
            "PUT",
            f"{resource_type}/{resource_id}",
            json=payload,
            headers={"Content-Type": "application/fhir+json"},
        )

    async def patch_resource(
        self,
        resource_type: str,
        resource_id: str,
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not operations:
            raise ValueError("FHIR PATCH requires at least one operation")
        return await self._request(
            "PATCH",
            f"{resource_type}/{resource_id}",
            json=operations,
            headers={"Content-Type": "application/json-patch+json"},
        )

    async def delete_resource(
        self, resource_type: str, resource_id: str
    ) -> dict[str, Any]:
        resource = await self.get_resource(resource_type, resource_id)
        if resource.get("resourceType") != resource_type:
            raise FHIRClientError(502, "FHIR repository returned the wrong resource type")
        if isinstance(resource.get("active"), bool):
            resource["active"] = False
        elif "status" in resource:
            resource["status"] = "entered-in-error"
        else:
            raise ValueError(
                f"{resource_type} does not expose a status field for soft deletion"
            )
        return await self.update_resource(resource_type, resource_id, resource)

    async def export_patient(self, health_id: str) -> tuple[list[dict[str, Any]], bytes]:
        bundle = await self._request(
            "GET", f"Patient/{health_id}/$everything", headers={"Accept": "application/fhir+json"}
        )
        resources: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        while True:
            entries = bundle.get("entry", [])
            if not isinstance(entries, list):
                raise FHIRClientError(502, "FHIR export returned an invalid Bundle")
            for entry in entries:
                resource = entry.get("resource") if isinstance(entry, dict) else None
                if isinstance(resource, dict):
                    resources.append(resource)
            next_url = next(
                (
                    link.get("url")
                    for link in bundle.get("link", [])
                    if isinstance(link, dict) and link.get("relation") == "next"
                ),
                None,
            )
            if not next_url:
                break
            if (
                not isinstance(next_url, str)
                or not next_url.startswith(self.base_url + "/")
                or next_url in seen_urls
            ):
                raise FHIRClientError(502, "FHIR export returned an invalid next-page URL")
            seen_urls.add(next_url)
            bundle = await self._request("GET", next_url)
        if not resources:
            raise FHIRClientError(404, "FHIR export returned no resources for this patient")
        package = json.dumps(
            resources, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return resources, package

    async def import_resources(
        self, resources: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not resources:
            raise ValueError("FHIR import requires at least one resource")
        entries = []
        for resource in resources:
            resource_type = resource.get("resourceType")
            if not isinstance(resource_type, str) or not resource_type:
                raise ValueError("Every imported FHIR resource must have a resourceType")
            resource_id = resource.get("id")
            request = (
                {"method": "PUT", "url": f"{resource_type}/{resource_id}"}
                if isinstance(resource_id, str) and resource_id
                else {"method": "POST", "url": resource_type}
            )
            entries.append({"resource": resource, "request": request})
        result = await self._request(
            "POST",
            "",
            json={"resourceType": "Bundle", "type": "transaction", "entry": entries},
            headers={
                "Content-Type": "application/fhir+json",
                "Accept": "application/fhir+json",
            },
        )
        for entry in result.get("entry", []):
            response = entry.get("response") if isinstance(entry, dict) else None
            if not isinstance(response, dict):
                continue
            code = str(response.get("status", ""))
            if code[:1] in {"4", "5"}:
                outcome = response.get("outcome")
                if isinstance(outcome, dict) and outcome.get("resourceType") == "OperationOutcome":
                    raise FHIRClientError(
                        502,
                        "FHIR destination rejected an imported resource",
                        outcome,
                    )
                raise FHIRClientError(
                    502, f"FHIR destination rejected an imported resource ({code})"
                )
        return result

    async def health_check(self) -> bool:
        try:
            await self.get_metadata()
            return True
        except (httpx.HTTPError, FHIRClientError):
            return False
