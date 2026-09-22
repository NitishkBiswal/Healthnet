from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class PatientIdentity(Base):
    """Single source of truth for permanent Health ID. UUID is true PK, display_health_id is permanent namespace label."""
    __tablename__ = "patient_identity"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 1

class PatientIdentifier(Base):
    """External/national IDs mapped to internal ID. Never the primary key, never on-chain."""
    __tablename__ = "patient_identifier"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 1

class PatientLocationHistory(Base):
    """Movement classification without touching identity."""
    __tablename__ = "patient_location_history"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 1
