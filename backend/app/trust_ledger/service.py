import hashlib
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.trust_ledger.models import TrustLedgerEntry
from app.trust_ledger.schemas import FORBIDDEN_FIELDS, LedgerEntryCreate

class TrustLedgerService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _validate_no_phi(request: LedgerEntryCreate) -> None:
        haystack = " ".join(str(v).lower() for v in request.model_dump().values() if v is not None)
        for field in FORBIDDEN_FIELDS:
            if field in haystack:
                raise ValueError(f"Forbidden sensitive content detected: {field}")

    async def record_entry(self, request: LedgerEntryCreate) -> TrustLedgerEntry:
        self._validate_no_phi(request)
        previous = await self.session.scalar(select(TrustLedgerEntry).order_by(TrustLedgerEntry.timestamp.desc(), TrustLedgerEntry.id.desc()))
        previous_hash = previous.entry_hash if previous else ""
        canonical = "|".join([previous_hash, request.transaction_id, request.event_type.value, request.opaque_subject_reference, str(request.source_repository_id or ""), str(request.destination_repository_id or ""), request.authorization_reference, request.package_hash, request.status, request.audit_reference or ""])
        entry = TrustLedgerEntry(**request.model_dump(), event_type=request.event_type.value, previous_entry_hash=previous_hash or None, entry_hash=hashlib.sha256(canonical.encode()).hexdigest())
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_entry(self, entry_id: UUID) -> TrustLedgerEntry | None:
        return await self.session.get(TrustLedgerEntry, entry_id)

    async def verify_chain(self) -> tuple[bool, int]:
        result = await self.session.execute(select(TrustLedgerEntry).order_by(TrustLedgerEntry.timestamp, TrustLedgerEntry.id))
        previous_hash = ""
        count = 0
        for entry in result.scalars():
            canonical = "|".join([previous_hash, entry.transaction_id, entry.event_type, entry.opaque_subject_reference, str(entry.source_repository_id or ""), str(entry.destination_repository_id or ""), entry.authorization_reference, entry.package_hash, entry.status, entry.audit_reference or ""])
            expected = hashlib.sha256(canonical.encode()).hexdigest()
            if expected != entry.entry_hash or (entry.previous_entry_hash or "") != previous_hash:
                return False, count
            previous_hash, count = entry.entry_hash, count + 1
        return True, count
