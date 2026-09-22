from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class RecordLocator(Base):
    """Pointer-only discovery index. Stores WHERE data is, never WHAT it is."""
    __tablename__ = "record_locator"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 3
