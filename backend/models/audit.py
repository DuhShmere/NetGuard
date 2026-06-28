from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from backend.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, index=True)
    device_id  = Column(Integer, ForeignKey("devices.id"), nullable=True)
    action     = Column(String, nullable=False)   # e.g. "remediate", "snapshot", "login"
    actor      = Column(String, nullable=False)   # username or "scheduler"
    detail     = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
