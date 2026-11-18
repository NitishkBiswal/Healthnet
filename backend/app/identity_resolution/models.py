"""Identity resolution models — match candidates and merge event log."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IdentityMatch(Base):
    """Stores the result of a probabilistic / deterministic identity match attempt."""

    __tablename__ = "identity_match"
    __table_args__ = {"schema": "healthnet"}

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    # The Health ID that was being registered / searched
    query_health_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    # The existing patient that was matched against
    candidate_health_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # Match method used
    match_method: Mapped[str] = mapped_column(String(32), nullable=False)  # DETERMINISTIC | PROBABILISTIC
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    band: Mapped[str] = mapped_column(String(16), nullable=False)  # HIGH | MEDIUM
    # Outcome of this match event
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # REGISTERED | DUPLICATE_REVIEW | LIKELY_DUPLICATE
    # Optional: ID of the DuplicateReview record if one was created
    duplicate_review_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdentityMergeEvent(Base):
    """Immutable record of every identity merge operation."""

    __tablename__ = "identity_merge_event"
    __table_args__ = {"schema": "healthnet"}

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    # Source identity that was superseded
    source_patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    source_health_id: Mapped[str] = mapped_column(String(32), nullable=False)
    # Target identity that survived
    target_patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    target_health_id: Mapped[str] = mapped_column(String(32), nullable=False)
    # Who authorized and performed the merge
    authorized_by: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    merged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdentityMatchConfiguration(Base):
    """Database-backed weights and cutoffs for identity resolution."""

    __tablename__ = "identity_match_configuration"
    __table_args__ = {"schema": "healthnet"}

    config_key: Mapped[str] = mapped_column(String(32), primary_key=True, default="default")
    name_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.45)
    date_of_birth_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.30)
    sex_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)
    phone_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.10)
    email_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.10)
    medium_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.70)
    high_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.90)
