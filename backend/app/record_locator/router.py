from fastapi import APIRouter, HTTPException

router = APIRouter(tags=['Record Locator'])

@router.post("/patients/{health_id}/record-locations")
async def create_record_location(health_id: str):
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 3")

@router.get("/patients/{health_id}/record-locations")
async def get_record_locations(health_id: str):
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 3")
