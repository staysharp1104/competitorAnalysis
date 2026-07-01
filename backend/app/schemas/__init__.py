from pydantic import BaseModel, Field
from typing import Optional, Any

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    product_line: Optional[str] = None
    industry: Optional[str] = None
    project_type: str = "single"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    product_line: Optional[str] = None
    industry: Optional[str] = None
    status: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str; name: str; description: Optional[str] = None
    product_line: Optional[str] = None; project_type: str; status: str
    industry: Optional[str] = None; config_snapshot: Optional[Any] = None
    created_at: Optional[str] = None; updated_at: Optional[str] = None

class PageCreate(BaseModel):
    project_id: str; title: Optional[str] = None; url: Optional[str] = None
    source_type: str = "paste"; raw_content: Optional[str] = None
    clean_content: Optional[str] = None; html_content: Optional[str] = None
    parent_id: Optional[str] = None

class PageUpdate(BaseModel):
    title: Optional[str] = None; raw_content: Optional[str] = None
    clean_content: Optional[str] = None; sort_order: Optional[int] = None

class PageResponse(BaseModel):
    id: str; project_id: str; parent_id: Optional[str] = None
    title: Optional[str] = None; url: Optional[str] = None; page_depth: int
    sort_order: int; source_type: str; raw_content: Optional[str] = None
    clean_content: Optional[str] = None; extra_meta: Optional[Any] = None
    created_at: Optional[str] = None; updated_at: Optional[str] = None

class FeatureNodeCreate(BaseModel):
    project_id: str; parent_id: Optional[str] = None; level: int
    node_type: str = "feature"; name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None; source_page_id: Optional[str] = None
    source_type: str = "manual"; tags: Optional[list] = None
    constraints: Optional[str] = None; validation_rules: Optional[str] = None
    acceptance_criteria: Optional[str] = None; confidence_score: Optional[float] = None
    strategy: Optional[str] = None

class FeatureNodeUpdate(BaseModel):
    name: Optional[str] = None; description: Optional[str] = None
    parent_id: Optional[str] = None; sort_order: Optional[int] = None
    tags: Optional[list] = None; constraints: Optional[str] = None
    validation_rules: Optional[str] = None; acceptance_criteria: Optional[str] = None
    status: Optional[str] = None

class FeatureNodeResponse(BaseModel):
    id: str; project_id: str; parent_id: Optional[str] = None
    sort_order: int; level: int; node_type: str; name: str
    description: Optional[str] = None; source_page_id: Optional[str] = None
    source_type: str; tags: Optional[Any] = None; constraints: Optional[str] = None
    validation_rules: Optional[str] = None; acceptance_criteria: Optional[str] = None
    status: str; confidence_score: Optional[float] = None
    strategy: Optional[str] = None; children: list = []
    created_at: Optional[str] = None; updated_at: Optional[str] = None

class AnalyzeRequest(BaseModel):
    project_id: str; page_ids: list[str] = Field(..., min_length=1)

class AnalyzeResponse(BaseModel):
    task_id: str; status: str; message: str

class ReportGenerateRequest(BaseModel):
    project_id: str; report_type: str = "reverse_prd"; export_format: str = "markdown"

class ReportResponse(BaseModel):
    id: str; project_id: str; report_name: str; report_type: str
    export_format: str; content: Optional[str] = None; status: str
    created_at: Optional[str] = None; updated_at: Optional[str] = None

class ComparisonCreate(BaseModel):
    project_id: str; name: str = "竞品对比分析"; competitor_ids: list[str] = Field(..., min_length=1)

class ComparisonResponse(BaseModel):
    id: str; project_id: str; name: str; competitor_ids: list[str]
    alignment_matrix: Optional[Any] = None; alignment_suggestions: Optional[Any] = None
    summary: Optional[str] = None; summary_content: Optional[str] = None; status: str
    created_at: Optional[str] = None; updated_at: Optional[str] = None

class AlignmentUpdate(BaseModel):
    alignment_matrix: dict
