from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class TrustLedgerEntry(Base):
    """Append-only integrity metadata. Never stores PHI/PII or clinical content."""
    __tablename__ = "trust_ledger_entry"
    __table_args__ = {"schema": "healthnet"}
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[str] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    opaque_subject_reference: Mapped[str] = mapped_column(String(256), index=True)
    source_repository_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    destination_repository_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    authorization_reference: Mapped[str] = mapped_column(String(256))
    package_hash: Mapped[str] = mapped_column(String(128))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    audit_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    previous_entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
