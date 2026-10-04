from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Jurisdiction(Base):
    __tablename__="jurisdiction"; __table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    code:Mapped[str]=mapped_column(String(32),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(160))
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class PolicyRule(Base):
    __tablename__="policy_rule"; __table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    jurisdiction_id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),index=True)
    name:Mapped[str]=mapped_column(String(160))
    purpose:Mapped[str]=mapped_column(String(128))
    scope:Mapped[str]=mapped_column(String(128))
    effect:Mapped[str]=mapped_column(String(16),default="ALLOW")
    description:Mapped[str|None]=mapped_column(Text,nullable=True)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
