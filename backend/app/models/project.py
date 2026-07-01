import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class Project(Base):
    __tablename__ = "projects"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False, comment="项目名称")
    description = Column(Text, comment="项目描述")
    product_line = Column(String(100), comment="所属产品线")
    project_type = Column(String(20), nullable=False, default="single", comment="项目类型: single/comparison")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/archived/deleted")
    industry = Column(String(100), comment="行业类型")
    config_snapshot = Column(JSON, comment="项目配置快照")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "product_line": self.product_line, "project_type": self.project_type,
            "status": self.status, "industry": self.industry,
            "config_snapshot": self.config_snapshot,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
