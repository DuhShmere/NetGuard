from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from backend.database import Base

class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(Integer, ForeignKey("devices.id"), nullable=False)
    score       = Column(Float, nullable=False)        # 0.0 - 100.0
    violations  = Column(JSON, default=list)           # list of failed rule IDs
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
