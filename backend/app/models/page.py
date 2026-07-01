import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, ForeignKey
from app.database import Base

def gen_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)

class CrawledPage(Base):
    __tablename__ = "crawled_pages"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, comment="所属项目")
    crawl_task_id = Column(String(36), ForeignKey("crawl_tasks.id"), comment="关联爬取任务")
    parent_id = Column(String(36), ForeignKey("crawled_pages.id"), comment="来源页面ID")
    title = Column(String(500), comment="页面标题")
    url = Column(String(2048), comment="页面URL（可选）")
    page_depth = Column(Integer, default=0, comment="页面深度")
    http_status = Column(Integer, comment="HTTP状态码")
    sort_order = Column(Integer, default=0, comment="排序")
    source_type = Column(String(20), nullable=False, default="manual", comment="来源: paste/html/pdf/url")
    raw_content = Column(Text, comment="原始内容（粘贴文本/提取文本）")
    clean_content = Column(Text, comment="降噪后的Markdown内容")
    extra_meta = Column(JSON, comment="页面元信息")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id, "project_id": self.project_id, "crawl_task_id": self.crawl_task_id,
            "parent_id": self.parent_id, "title": self.title, "url": self.url,
            "page_depth": self.page_depth, "http_status": self.http_status,
            "sort_order": self.sort_order, "source_type": self.source_type,
            "raw_content": self.raw_content, "clean_content": self.clean_content,
            "extra_meta": self.extra_meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class PageContent(Base):
    __tablename__ = "page_contents"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    page_id = Column(String(36), ForeignKey("crawled_pages.id"), unique=True, nullable=False)
    raw_html = Column(Text, comment="原始HTML（HTML上传时）")
    clean_html = Column(Text, comment="降噪后HTML")
    markdown_content = Column(Text, comment="Markdown内容")
    word_count = Column(Integer, default=0, comment="字数统计")
    language = Column(String(10), comment="语言")
    extracted_at = Column(DateTime, default=utcnow)
