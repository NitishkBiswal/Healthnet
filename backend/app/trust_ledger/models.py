from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class TrustLedgerEntry(Base):
    """
    ONLY permitted fields: transaction_id, event_type, opaque_subject_reference,
    source_repository_id, destination_repository_id, authorization_reference,
    package_hash, timestamp, status, audit_reference
    """
    __tablename__ = "trust_ledger_entry"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 11
