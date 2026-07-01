import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, Boolean, ForeignKey, DECIMAL
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class AnalysisReport(Base):
    __tablename__ = "analysis_reports"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    report_name = Column(String(200), nullable=False)
    report_type = Column(String(30), nullable=False, comment="reverse_prd/feature_matrix/comparison_report")
    export_format = Column(String(20), nullable=False, default="markdown", comment="markdown/excel/json")
    content = Column(Text, comment="报告内容（Markdown/JSON）")
    status = Column(String(20), nullable=False, default="generating", comment="generating/completed/failed")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

class AnalysisTemplate(Base):
    __tablename__ = "analysis_templates"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), comment="NULL=全局模板")
    template_name = Column(String(200), nullable=False)
    template_type = Column(String(30), nullable=False, comment="b端后台/c端产品/saas/自定义")
    description = Column(Text)
    dimensions = Column(JSON, nullable=False, comment="拆解维度配置")
    prompt_template = Column(Text, nullable=False, comment="Prompt模板")
    placeholder_vars = Column(JSON, comment="变量定义")
    is_system = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
