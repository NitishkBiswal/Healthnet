from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,String,Text,Uuid,func
from sqlalchemy.orm import Mapped,mapped_column
from app.core.database import Base
class RecordProvenance(Base):
    __tablename__="record_provenance";__table_args__={"schema":"healthnet"}
    id:Mapped[UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid4)
    health_id:Mapped[str]=mapped_column(String(32),index=True)
    repository_id:Mapped[UUID|None]=mapped_column(Uuid(as_uuid=True),nullable=True,index=True)
    resource_type:Mapped[str]=mapped_column(String(64))
    resource_id:Mapped[str]=mapped_column(String(128))
    source_system:Mapped[str]=mapped_column(String(256))
    actor_id:Mapped[str]=mapped_column(String(128))
    action:Mapped[str]=mapped_column(String(64))
    details:Mapped[str]=mapped_column(Text,default="{}")
    recorded_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
