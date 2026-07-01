"""对比分析数据模型"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class ComparisonAnalysis(Base):
    __tablename__ = "comparison_analyses"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, comment="基准项目ID")
    name = Column(String(200), nullable=False, comment="对比分析名称")
    competitor_ids = Column(JSON, nullable=False, comment="竞品项目ID列表")
    alignment_matrix = Column(JSON, comment="功能对齐矩阵")
    alignment_suggestions = Column(JSON, comment="AI自动对齐建议")
    summary = Column(Text, comment="对比分析总结")
    summary_content = Column(Text, comment="对比报告Markdown内容")
    status = Column(String(20), nullable=False, default="pending", comment="pending/aligning/completed/failed")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
