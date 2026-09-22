from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class EmergencyHealthProfile(Base):
    __tablename__ = "emergency_health_profile"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 9
