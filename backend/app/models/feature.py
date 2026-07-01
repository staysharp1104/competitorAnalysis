import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey, DECIMAL
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class FeatureNode(Base):
    __tablename__ = "feature_nodes"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, comment="所属项目")
    parent_id = Column(String(36), ForeignKey("feature_nodes.id"), comment="父节点ID")
    sort_order = Column(Integer, default=0, comment="同级排序")
    level = Column(Integer, nullable=False, comment="层级: 1=模块 2=页面 3=功能点")
    node_type = Column(String(20), nullable=False, comment="module/page/feature")
    name = Column(String(200), nullable=False, comment="节点名称")
    description = Column(Text, comment="功能描述")
    source_page_id = Column(String(36), ForeignKey("crawled_pages.id"), comment="来源页面ID")
    source_type = Column(String(20), nullable=False, default="auto", comment="auto/manual/user_input")
    tags = Column(JSON, comment="标签数组")
    constraints = Column(Text, comment="约束条件")
    validation_rules = Column(Text, comment="校验规则")
    acceptance_criteria = Column(Text, comment="验收标准")
    status = Column(String(20), nullable=False, default="active", comment="active/deprecated/planned")
    confidence_score = Column(DECIMAL(3, 2), comment="置信度 0.00-1.00")
    strategy = Column(String(64), comment="分析策略来源: mimo/v2_structured/v1_text_fallback/nav_fallback/mimo_nav_fallback")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "project_id": self.project_id, "parent_id": self.parent_id,
            "sort_order": self.sort_order, "level": self.level, "node_type": self.node_type,
            "name": self.name, "description": self.description, "source_page_id": self.source_page_id,
            "source_type": self.source_type, "tags": self.tags,
            "constraints": self.constraints, "validation_rules": self.validation_rules,
            "acceptance_criteria": self.acceptance_criteria, "status": self.status,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "strategy": self.strategy,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
