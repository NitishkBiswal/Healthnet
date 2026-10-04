from typing import Any
from pydantic import BaseModel,Field
class FHIRResource(BaseModel):
    resourceType:str
    id:str|None=None
    model_config={"extra":"allow"}
class FHIRBundle(BaseModel):
    resourceType:str="Bundle"
    type:str
    total:int|None=None
    entry:list[dict[str,Any]]=Field(default_factory=list)
class FHIRCapabilityStatement(BaseModel):
    resourceType:str
    status:str|None=None
    fhirVersion:str|None=None
    format:list[str]=Field(default_factory=list)
