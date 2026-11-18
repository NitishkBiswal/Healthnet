from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID

from app.core.database import Base


class ProviderNoticeDismissal(Base):
    __tablename__ = "provider_notice_dismissal"
    __table_args__ = {"schema": "healthnet"}

    consent_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("healthnet.consent.id"), primary_key=True
    )
    provider_subject: Mapped[str] = mapped_column(String(128), primary_key=True)
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
