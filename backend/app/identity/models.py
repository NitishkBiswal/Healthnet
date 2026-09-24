from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IdentityStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


class DuplicateReviewStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED_DUPLICATE = "APPROVED_DUPLICATE"
    REJECTED = "REJECTED"


class PatientIdentity(Base):
    """Global patient identity. Clinical records never belong in this table."""

    __tablename__ = "patient_identity"
    __table_args__ = {"schema": "healthnet"}

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    display_health_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    issuing_jurisdiction: Mapped[str] = mapped_column(String(32), index=True)
    given_name: Mapped[str] = mapped_column(String(100))
    family_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default=IdentityStatus.ACTIVE.value)
    superseded_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("healthnet.patient_identity.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PatientIdentifier(Base):
    """External identifiers mapped to an internal identity; never the primary key."""

    __tablename__ = "patient_identifier"
    __table_args__ = {"schema": "healthnet"}

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("healthnet.patient_identity.id"), index=True
    )
    identifier_type: Mapped[str] = mapped_column(String(64))
    identifier_value: Mapped[str] = mapped_column(String(256))
    issuing_authority: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PatientLocationHistory(Base):
    """Movement classification without changing the permanent Health ID."""

    __tablename__ = "patient_location_history"
    __table_args__ = {"schema": "healthnet"}

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("healthnet.patient_identity.id"), index=True
    )
    jurisdiction: Mapped[str] = mapped_column(String(32))
    movement_type: Mapped[str] = mapped_column(String(40))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DuplicateReview(Base):
    """Human-review queue for uncertain identity matches."""

    __tablename__ = "duplicate_review"
    __table_args__ = {"schema": "healthnet"}

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    candidate_patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("healthnet.patient_identity.id"), index=True
    )
    proposed_given_name: Mapped[str] = mapped_column(String(100))
    proposed_family_name: Mapped[str] = mapped_column(String(100))
    proposed_date_of_birth: Mapped[date] = mapped_column(Date)
    proposed_sex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    proposed_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    proposed_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    confidence: Mapped[float] = mapped_column()
    status: Mapped[str] = mapped_column(
        String(32), default=DuplicateReviewStatus.PENDING.value, index=True
    )
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
