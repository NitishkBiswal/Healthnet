from typing import Any


class FHIRResourceMapper:
    """Maps between HealthNet internal models and FHIR R4 resources."""

    def to_fhir(self, internal_model: Any) -> dict[str, Any]:
        # TODO: Implement in Segment 7
        raise NotImplementedError("FHIR resource mapping is implemented in Segment 7")

    def from_fhir(self, fhir_resource: dict[str, Any]) -> Any:
        # TODO: Implement in Segment 7
        raise NotImplementedError("FHIR resource mapping is implemented in Segment 7")
