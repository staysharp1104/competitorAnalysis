"""项目图片资源模型"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class ProjectImage(Base):
    __tablename__ = "project_images"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True, comment="所属项目ID")
    page_node_id = Column(String(36), ForeignKey("feature_nodes.id"), comment="关联的功能树页面节点ID")
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(512), nullable=False, comment="存储路径")
    file_size = Column(Integer, comment="文件大小，字节")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(String(20), default="pending", comment="pending/processing/completed/failed")
    error_msg = Column(String(500), comment="错误信息")
    created_at = Column(DateTime, nullable=False, default=utcnow)
