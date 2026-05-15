"""
Device model
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Device(Base):
    """网络设备"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    ip = Column(String(50), nullable=False)
    status = Column(String(20), default="unknown")  # online, offline, unknown
    device_type = Column(String(50))
    vendor = Column(String(50))
    model = Column(String(100))
    credential_group = Column(String(50), default="default")
    description = Column(Text)
    location = Column(String(255))
    snmp_community = Column(String(100))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
