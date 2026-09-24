from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Consent"])


@router.post("/consents")
async def create_consent() -> None:
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 5")


@router.get("/consents/{consent_id}")
async def get_consent(consent_id: str) -> None:
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 5")


@router.delete("/consents/{consent_id}")
async def delete_consent(consent_id: str) -> None:
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 5")


@router.get("/patients/{health_id}/consents")
async def get_patient_consents(health_id: str) -> None:
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 5")
