from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class RecordLocator(Base):
    __tablename__ = "record_locator"
    __table_args__ = {"schema": "healthnet"}
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    health_id: Mapped[str] = mapped_column(String(32), index=True)
    repository_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("healthnet.repository.id"), index=True)
    endpoint: Mapped[str] = mapped_column(String(512))
    resource_types: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", index=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
