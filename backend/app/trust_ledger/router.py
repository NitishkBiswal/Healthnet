from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["Trust Ledger"])


@router.post("/ledger/entries")
async def create_ledger_entry() -> None:
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 11")


@router.get("/ledger/entries/{entry_id}")
async def get_ledger_entry(entry_id: str) -> None:
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 11")


@router.get("/ledger/verify")
async def verify_ledger() -> None:
    raise HTTPException(status_code=501, detail="Not Implemented: Segment 11")
