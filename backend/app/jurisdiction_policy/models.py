from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class PolicyRule(Base):
    __tablename__ = "policy_rule"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 6

class Jurisdiction(Base):
    __tablename__ = "jurisdiction"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 6
