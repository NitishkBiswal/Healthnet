from fastapi import APIRouter, HTTPException

router = APIRouter(tags=['Identity'])

@router.post("/register")
async def register_patient():
    """Register a new patient (FR-1)."""
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 1")

@router.get("/{health_id}")
async def get_patient(health_id: str):
    """Get patient by health ID (FR-1)."""
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 1")

@router.get("/{health_id}/identifiers")
async def get_patient_identifiers(health_id: str):
    """Get patient identifiers (FR-1)."""
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 1")
