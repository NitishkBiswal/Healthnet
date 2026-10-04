from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class TransferRequest(Base):
    __tablename__ = "transfer_request"; __table_args__ = {"schema": "healthnet"}
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    health_id: Mapped[str] = mapped_column(String(32), index=True)
    source_repository_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("healthnet.repository.id"))
    destination_repository_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("healthnet.repository.id"))
    requested_by: Mapped[str] = mapped_column(String(128))
    purpose: Mapped[str] = mapped_column(String(128))
    scope: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(40), index=True)
    authorization_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    package_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TransferAuthorizationToken(Base):
    __tablename__ = "transfer_authorization_token"; __table_args__ = {"schema": "healthnet"}
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    transfer_request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("healthnet.transfer_request.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    issued_by: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class TransferManifest(Base):
    __tablename__ = "transfer_manifest"; __table_args__ = {"schema": "healthnet"}
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    transfer_request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("healthnet.transfer_request.id"), index=True)
    resource_count: Mapped[int] = mapped_column(Integer, default=0)
    manifest_hash: Mapped[str] = mapped_column(String(64))
    package_hash: Mapped[str] = mapped_column(String(128))
    validation_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
