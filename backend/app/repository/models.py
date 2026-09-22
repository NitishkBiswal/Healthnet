from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class Repository(Base):
    __tablename__ = "repository"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 2

class EHRCustody(Base):
    __tablename__ = "ehr_custody"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 2
