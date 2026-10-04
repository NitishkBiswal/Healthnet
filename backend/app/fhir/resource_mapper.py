from typing import Any
class FHIRResourceMapper:
    def to_fhir(self,internal_model:Any)->dict[str,Any]:
        if isinstance(internal_model,dict): return internal_model
        if hasattr(internal_model,"model_dump"): return internal_model.model_dump(exclude_none=True)
        if hasattr(internal_model,"__dict__"): return {k:v for k,v in internal_model.__dict__.items() if not k.startswith("_") and v is not None}
        raise TypeError("Unsupported internal model")
    def from_fhir(self,fhir_resource:dict[str,Any])->dict[str,Any]: return dict(fhir_resource)
