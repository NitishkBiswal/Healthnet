from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,String,Text,Uuid,func
from sqlalchemy.orm import Mapped,mapped_column
from app.core.database import Base
class EmergencyHealthProfile(Base):
    __tablename__="emergency_health_profile";__table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    health_id:Mapped[str]=mapped_column(String(32),unique=True,index=True)
    blood_group:Mapped[str|None]=mapped_column(String(8),nullable=True)
    allergies:Mapped[str]=mapped_column(Text,default="")
    medications:Mapped[str]=mapped_column(Text,default="")
    conditions:Mapped[str]=mapped_column(Text,default="")
    emergency_contacts:Mapped[str]=mapped_column(Text,default="")
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
class BreakGlassEvent(Base):
    __tablename__="break_glass_event";__table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    health_id:Mapped[str]=mapped_column(String(32),index=True)
    actor_id:Mapped[str]=mapped_column(String(128))
    reason:Mapped[str]=mapped_column(Text)
    invoked_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
