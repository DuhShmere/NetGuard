from sqlalchemy import Column, Integer, String, Enum
from backend.database import Base
import enum

class Vendor(str, enum.Enum):
    cisco = "cisco"
    juniper = "juniper"

class Device(Base):
    __tablename__ = "devices"

    id       = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, nullable=False)
    ip       = Column(String, nullable=False)
    vendor   = Column(Enum(Vendor), nullable=False)
    platform = Column(String, nullable=True)  # e.g. "ios", "nxos", "junos"
    port     = Column(Integer, default=22)
