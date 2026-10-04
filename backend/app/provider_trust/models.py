from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Organization(Base):
    __tablename__="organization"; __table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    external_id:Mapped[str]=mapped_column(String(128),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(200))
    jurisdiction:Mapped[str]=mapped_column(String(32),index=True)
    trust_status:Mapped[str]=mapped_column(String(16),default="ACTIVE",index=True)
    issuer:Mapped[str|None]=mapped_column(String(512),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class Provider(Base):
    __tablename__="provider"; __table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    external_id:Mapped[str]=mapped_column(String(128),unique=True,index=True)
    given_name:Mapped[str]=mapped_column(String(100))
    family_name:Mapped[str]=mapped_column(String(100))
    license_number:Mapped[str]=mapped_column(String(128),unique=True,index=True)
    jurisdiction:Mapped[str]=mapped_column(String(32))
    trust_status:Mapped[str]=mapped_column(String(16),default="ACTIVE",index=True)
    keycloak_subject:Mapped[str|None]=mapped_column(String(128),unique=True,nullable=True,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class PractitionerRole(Base):
    __tablename__="practitioner_role"; __table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    provider_id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),ForeignKey("healthnet.provider.id"),index=True)
    organization_id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),ForeignKey("healthnet.organization.id"),index=True)
    role:Mapped[str]=mapped_column(String(32))
    active:Mapped[bool]=mapped_column(Boolean,default=True)
