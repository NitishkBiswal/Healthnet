from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.security.dependencies import require_role
from app.security.rbac import Role
from app.trust_ledger.schemas import LedgerEntryCreate, LedgerEntryResponse
from app.trust_ledger.service import TrustLedgerService

router = APIRouter(tags=["Trust Ledger"])

@router.post("/ledger/entries", response_model=LedgerEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_ledger_entry(request: LedgerEntryCreate, _: dict = Depends(require_role(Role.SYSTEM)), session: AsyncSession = Depends(get_db)):
    try:
        entry = await TrustLedgerService(session).record_entry(request)
        await session.commit()
        return LedgerEntryResponse.model_validate(entry)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc

@router.get("/ledger/entries/{entry_id}", response_model=LedgerEntryResponse)
async def get_ledger_entry(entry_id: UUID, _: dict = Depends(require_role(Role.AUDITOR)), session: AsyncSession = Depends(get_db)):
    entry = await TrustLedgerService(session).get_entry(entry_id)
    if entry is None:
        raise HTTPException(404, "Ledger entry not found")
    return LedgerEntryResponse.model_validate(entry)

@router.get("/ledger/verify")
async def verify_ledger(_: dict = Depends(require_role(Role.AUDITOR)), session: AsyncSession = Depends(get_db)):
    valid, entries_checked = await TrustLedgerService(session).verify_chain()
    return {"valid": valid, "entries_checked": entries_checked}
