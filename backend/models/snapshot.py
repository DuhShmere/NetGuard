from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database import Base

class ConfigSnapshot(Base):
    __tablename__ = "snapshots"

    id         = Column(Integer, primary_key=True, index=True)
    device_id  = Column(Integer, ForeignKey("devices.id"), nullable=False)
    config     = Column(Text, nullable=False)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    triggered_by = Column(String, default="scheduler")
