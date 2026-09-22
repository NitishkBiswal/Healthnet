from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class AuditEvent(Base):
    """prev_event_hash -> event_hash chain for tamper detection"""
    __tablename__ = "audit_event"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 10
