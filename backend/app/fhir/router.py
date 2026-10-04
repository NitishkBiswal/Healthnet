from fastapi import APIRouter,HTTPException
from app.fhir.client import FHIRClient
from app.fhir.schemas import FHIRResource
router=APIRouter(tags=["FHIR"])
@router.get("/metadata")
async def metadata():
    try:return await FHIRClient().get_metadata()
    except Exception as exc:raise HTTPException(502,"FHIR repository unavailable") from exc
@router.get("/{resource_type}/{resource_id}")
async def get_resource(resource_type:str,resource_id:str):
    try:return await FHIRClient().get_resource(resource_type,resource_id)
    except Exception as exc:raise HTTPException(502,"FHIR repository unavailable") from exc
@router.get("/{resource_type}")
async def search(resource_type:str): return await FHIRClient().search(resource_type,{})
@router.post("/{resource_type}")
async def create(resource_type:str,resource:FHIRResource):
    try:return await FHIRClient().create_resource(resource_type,resource.model_dump(exclude_none=True))
    except Exception as exc:raise HTTPException(502,"FHIR repository unavailable") from exc
