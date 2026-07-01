"""错误日志模型 - 项目监控"""
from sqlalchemy import Column, String, Text, DateTime, Integer
from app.database import Base
from app.models.analysis import gen_uuid, utcnow

class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    level = Column(String(20), nullable=False, default="error", comment="级别: error/warning/info")
    source = Column(String(100), comment="来源模块/路由")
    message = Column(String(500), nullable=False, comment="错误摘要")
    detail = Column(Text, comment="详细错误信息/堆栈")
    path = Column(String(500), comment="请求路径")
    method = Column(String(10), comment="HTTP 方法")
    project_id = Column(String(36), comment="关联项目ID")
    status_code = Column(Integer, comment="HTTP 状态码")
    created_at = Column(DateTime, nullable=False, default=utcnow)
