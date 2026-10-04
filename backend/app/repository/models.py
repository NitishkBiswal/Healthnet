from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class RepositoryStatus:
    ONLINE="ONLINE"; OFFLINE="OFFLINE"; DEGRADED="DEGRADED"

class Repository(Base):
    __tablename__="repository"; __table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    code:Mapped[str]=mapped_column(String(64),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(160))
    jurisdiction:Mapped[str]=mapped_column(String(32),index=True)
    base_url:Mapped[str]=mapped_column(String(512))
    status:Mapped[str]=mapped_column(String(16),default=RepositoryStatus.ONLINE,index=True)
    description:Mapped[str|None]=mapped_column(Text,nullable=True)
    last_checked_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

class EHRCustody(Base):
    __tablename__="ehr_custody"; __table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    health_id:Mapped[str]=mapped_column(String(32),index=True)
    repository_id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),ForeignKey("healthnet.repository.id"),index=True)
    resource_types:Mapped[str]=mapped_column(String(512))
    custody_start:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    custody_end:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
