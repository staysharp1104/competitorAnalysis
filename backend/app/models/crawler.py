import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class CrawlTask(Base):
    __tablename__ = "crawl_tasks"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, comment="所属项目")
    root_url = Column(String(2048), nullable=False, comment="入口URL")
    status = Column(String(20), nullable=False, default="pending", comment="pending/running/paused/completed/failed/cancelled")
    max_depth = Column(Integer, default=3, comment="最大爬取深度")
    max_pages = Column(Integer, default=100, comment="最大爬取页面数")
    pages_discovered = Column(Integer, default=0, comment="已发现页面数")
    pages_downloaded = Column(Integer, default=0, comment="已下载页面数")
    pages_filtered = Column(Integer, default=0, comment="已过滤页面数")
    pages_failed = Column(Integer, default=0, comment="失败页面数")
    config = Column(JSON, comment="爬取配置（exclude_patterns等）")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
