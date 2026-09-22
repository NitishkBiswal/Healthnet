from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class IdentityMatch(Base):
    __tablename__ = "identity_match"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 1

class IdentityMergeEvent(Base):
    __tablename__ = "identity_merge_event"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 1
