from fastapi import APIRouter, HTTPException

router = APIRouter(tags=['Audit'])

@router.get("/audit/{event_id}")
async def get_audit_event(event_id: str):
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 10")

@router.get("/audit/patient/{health_id}")
async def get_patient_audit_events(health_id: str):
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 10")
