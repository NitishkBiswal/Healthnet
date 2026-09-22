from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class Organization(Base):
    __tablename__ = "organization"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 4

class Provider(Base):
    __tablename__ = "provider"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 4

class PractitionerRole(Base):
    __tablename__ = "practitioner_role"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 4
