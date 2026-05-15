"""
Config Template model
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from app.core.database import Base


class ConfigTemplate(Base):
    """配置模板"""
    __tablename__ = "config_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    content = Column(Text)  # 模板内容
    variables = Column(JSON)  # 变量定义
    vendor = Column(String(50))
    device_type = Column(String(50))
    version = Column(String(20), default="1.0")
    created_by = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
