from pydantic import BaseModel, Field
from typing import Optional, Any

class CrawlTaskCreate(BaseModel):
    project_id: str; root_url: str = Field(..., min_length=1, max_length=2048)
    max_depth: int = Field(default=3, ge=1, le=10); max_pages: int = Field(default=100, ge=1, le=1000)
    exclude_patterns: Optional[list[str]] = None

class CrawlTaskResponse(BaseModel):
    id: str; project_id: str; root_url: str; status: str; max_depth: int; max_pages: int
    pages_discovered: int = 0; pages_downloaded: int = 0; pages_filtered: int = 0; pages_failed: int = 0
    config: Optional[Any] = None; error_message: Optional[str] = None
    created_at: Optional[str] = None; updated_at: Optional[str] = None

class CrawlTaskProgressResponse(BaseModel):
    id: str; status: str; pages_discovered: int; pages_downloaded: int
    pages_filtered: int; pages_failed: int; max_pages: int; max_depth: int
    current_url: Optional[str] = None

class CrawlTaskPageItem(BaseModel):
    id: str; title: Optional[str] = None; url: Optional[str] = None
    page_depth: int = 0; http_status: Optional[int] = None
    source_type: str = "crawl"; word_count: int = 0; created_at: Optional[str] = None

class CrawlTaskPageSelection(BaseModel):
    page_ids: list[str]; model: str = "deepseek"

class CrawlTaskAnalyzeResponse(BaseModel):
    task_id: str; status: str; message: str
