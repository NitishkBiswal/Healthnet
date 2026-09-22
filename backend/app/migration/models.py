from sqlalchemy import Column, Uuid
from uuid import uuid4
from app.core.database import Base

class TransferRequest(Base):
    __tablename__ = "transfer_request"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 12

class TransferAuthorizationToken(Base):
    __tablename__ = "transfer_authorization_token"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 12

class TransferManifest(Base):
    __tablename__ = "transfer_manifest"
    __table_args__ = {"schema": "healthnet"}
    id = Column(Uuid, primary_key=True, default=uuid4)
    # TODO: Implement in Segment 12
