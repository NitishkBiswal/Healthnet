"""Shared SQLAlchemy model base and mixins."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy import UUID as SA_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

__all__ = ["Base", "TimestampMixin", "UUIDPrimaryKeyMixin"]


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )


class UUIDPrimaryKeyMixin:
    """Mixin to add a UUID primary key."""
    id: Mapped[UUID] = mapped_column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
