from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.security.dependencies import get_current_user, require_role
from app.security.rbac import Role
from app.trust_ledger.schemas import LedgerEntryCreate, LedgerEntryResponse
from app.trust_ledger.service import TrustLedgerService

router = APIRouter(tags=["Trust Ledger"])

require_system = require_role(Role.SYSTEM)
require_auditor = require_role(Role.AUDITOR)


async def require_admin_or_auditor(
    user: dict = Depends(get_current_user),
) -> dict:
    roles = set(user.get("roles", []))
    if not roles.intersection({Role.ADMIN.value, Role.AUDITOR.value}):
        raise HTTPException(403, "Admin or auditor role required")
    return user

@router.post("/ledger/entries", response_model=LedgerEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_ledger_entry(request: LedgerEntryCreate, _: dict = Depends(require_system), session: AsyncSession = Depends(get_db)):
    try:
        entry = await TrustLedgerService(session).record_entry(request)
        await session.commit()
        return LedgerEntryResponse.model_validate(entry)
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(400, str(exc)) from exc

@router.get("/ledger/entries/{entry_id}", response_model=LedgerEntryResponse)
async def get_ledger_entry(entry_id: UUID, _: dict = Depends(require_auditor), session: AsyncSession = Depends(get_db)):
    entry = await TrustLedgerService(session).get_entry(entry_id)
    if entry is None:
        raise HTTPException(404, "Ledger entry not found")
    return LedgerEntryResponse.model_validate(entry)

@router.get("/ledger/verify")
async def verify_ledger(
    _: dict = Depends(require_admin_or_auditor),
    session: AsyncSession = Depends(get_db),
):
    valid, entries_checked = await TrustLedgerService(session).verify_chain()
    return {"valid": valid, "entries_checked": entries_checked}
