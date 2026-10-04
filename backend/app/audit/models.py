from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,String,Text,Uuid,func
from sqlalchemy.orm import Mapped,mapped_column
from app.core.database import Base
class AuditEvent(Base):
    __tablename__="audit_event";__table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    event_type:Mapped[str]=mapped_column(String(32),index=True)
    health_id:Mapped[str|None]=mapped_column(String(32),index=True,nullable=True)
    actor_id:Mapped[str]=mapped_column(String(128),index=True)
    action:Mapped[str]=mapped_column(String(160))
    payload:Mapped[str]=mapped_column(Text,default="{}")
    prev_event_hash:Mapped[str|None]=mapped_column(String(64),nullable=True)
    event_hash:Mapped[str]=mapped_column(String(64),unique=True,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
