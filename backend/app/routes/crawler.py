import json, os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.project import Project
from app.models.page import CrawledPage, PageContent
from app.models.crawler import CrawlTask
from app.services.crawler_service import CrawlerService
from app.services.ai_analyzer import AIAnalyzer
from app.services.screenshot_service import ScreenshotService
from app.config import settings
from app.schemas.crawler import CrawlTaskCreate, CrawlTaskResponse, CrawlTaskProgressResponse, CrawlTaskPageItem, CrawlTaskPageSelection, CrawlTaskAnalyzeResponse

router = APIRouter(prefix="/api/crawl", tags=["crawler"])
crawler_service = CrawlerService()
ai_analyzer = AIAnalyzer()

@router.get("", response_model=list[CrawlTaskResponse])
async def list_crawl_tasks(project_id: str = Query(...), db: AsyncSession = Depends(get_db)):
    stmt = select(CrawlTask).where(CrawlTask.project_id == project_id).order_by(CrawlTask.created_at.desc())
    result = await db.execute(stmt)
    return [t.to_dict() for t in result.scalars().all()]

@router.post("/tasks", response_model=CrawlTaskResponse)
async def create_crawl_task(data: CrawlTaskCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == data.project_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none(): raise HTTPException(status_code=404, detail="项目不存在")
    active_stmt = select(CrawlTask).where(CrawlTask.project_id == data.project_id, CrawlTask.status.in_(["pending", "running"]))
    active_result = await db.execute(active_stmt)
    if active_result.scalar_one_or_none(): raise HTTPException(status_code=400, detail="该项目已有正在运行的任务")
    task = await crawler_service.create_and_start_task(data, db)
    return task.to_dict()

@router.get("/tasks/{task_id}", response_model=CrawlTaskResponse)
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CrawlTask).where(CrawlTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    return task.to_dict()

@router.get("/tasks/{task_id}/progress", response_model=CrawlTaskProgressResponse)
async def get_task_progress(task_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CrawlTask).where(CrawlTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    current_url = (task.config or {}).get("current_url", "") if task.config else ""
    return CrawlTaskProgressResponse(id=task.id, status=task.status, pages_discovered=task.pages_discovered or 0, pages_downloaded=task.pages_downloaded or 0, pages_filtered=task.pages_filtered or 0, pages_failed=task.pages_failed or 0, max_pages=task.max_pages or 100, max_depth=task.max_depth or 3, current_url=current_url)

@router.get("/tasks/{task_id}/pages", response_model=list[CrawlTaskPageItem])
async def list_task_pages(task_id: str, http_status: int = Query(None), depth: int = Query(None), keyword: str = Query(None), db: AsyncSession = Depends(get_db)):
    task_stmt = select(CrawlTask).where(CrawlTask.id == task_id)
    if not (await db.execute(task_stmt)).scalar_one_or_none(): raise HTTPException(status_code=404, detail="任务不存在")
    pages_stmt = select(CrawledPage).where(CrawledPage.crawl_task_id == task_id)
    if http_status is not None: pages_stmt = pages_stmt.where(CrawledPage.http_status == http_status)
    if depth is not None: pages_stmt = pages_stmt.where(CrawledPage.page_depth == depth)
    if keyword: pages_stmt = pages_stmt.where((CrawledPage.title.ilike(f"%{keyword}%")) | (CrawledPage.url.ilike(f"%{keyword}%")))
    pages_stmt = pages_stmt.order_by(CrawledPage.page_depth, CrawledPage.created_at)
    pages = (await db.execute(pages_stmt)).scalars().all()
    return [CrawlTaskPageItem(id=p.id, title=p.title, url=p.url, page_depth=p.page_depth or 0, http_status=p.http_status, source_type=p.source_type, word_count=(p.extra_meta or {}).get("word_count", 0) if p.extra_meta else 0, created_at=p.created_at.isoformat() if p.created_at else None) for p in pages]

@router.post("/tasks/{task_id}/pause", response_model=dict)
async def pause_task(task_id: str, db: AsyncSession = Depends(get_db)):
    if not await crawler_service.pause_task(task_id, db): raise HTTPException(status_code=400, detail="任务无法暂停")
    return {"status": "paused"}

@router.post("/tasks/{task_id}/resume", response_model=dict)
async def resume_task(task_id: str, db: AsyncSession = Depends(get_db)):
    if not await crawler_service.resume_task(task_id, db): raise HTTPException(status_code=400, detail="任务无法恢复")
    return {"status": "resumed"}

@router.post("/tasks/{task_id}/cancel", response_model=dict)
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    if not await crawler_service.cancel_task(task_id, db): raise HTTPException(status_code=400, detail="任务无法取消")
    return {"status": "cancelled"}

@router.delete("/tasks/{task_id}")
async def delete_crawl_task(task_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CrawlTask).where(CrawlTask.id == task_id)
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    pages = (await db.execute(select(CrawledPage).where(CrawledPage.crawl_task_id == task_id))).scalars()
    for page in pages:
        await db.execute(delete(PageContent).where(PageContent.page_id == page.id))
        await db.delete(page)
    await db.delete(task); await db.commit()
    return {"message": "删除成功"}

@router.post("/tasks/{task_id}/analyze", response_model=CrawlTaskAnalyzeResponse)
async def analyze_task_pages(task_id: str, data: CrawlTaskPageSelection, db: AsyncSession = Depends(get_db)):
    task = (await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))).scalar_one_or_none()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    pages = (await db.execute(select(CrawledPage).where(CrawledPage.id.in_(data.page_ids), CrawledPage.crawl_task_id == task_id, CrawledPage.http_status == 200))).scalars().all()
    if not pages: raise HTTPException(status_code=400, detail="没有可用的页面进行分析")
    project = (await db.execute(select(Project).where(Project.id == task.project_id))).scalar_one_or_none()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")
    pages_data = [{"id": p.id, "title": p.title, "clean_content": p.clean_content or p.raw_content or "", "struct_elements": (p.extra_meta or {}).get("struct_elements"), "screenshot_path": (p.extra_meta or {}).get("screenshot_path")} for p in pages]
    result_data = await ai_analyzer.analyze_pages(pages=pages_data, site_name=project.name, industry=project.industry or "", model=data.model)
    from app.models.feature import FeatureNode
    modules = result_data.get("modules", [])
    module_sort = 0; feature_count = 0
    for mod in modules:
        module_sort += 1
        module_node = FeatureNode(project_id=task.project_id, parent_id=None, sort_order=module_sort, level=1, node_type="module", name=mod.get("name", "未命名模块"), description=mod.get("description", ""), source_type="auto", confidence_score=0.85)
        db.add(module_node); await db.flush(); await db.refresh(module_node)
        page_sort = 0
        for page_data in mod.get("pages", []):
            page_sort += 1
            db.add(FeatureNode(project_id=task.project_id, parent_id=module_node.id, sort_order=page_sort, level=2, node_type="page", name=page_data.get("name", "未命名页面"), description=page_data.get("description", ""), source_type="auto", confidence_score=0.85, strategy=page_data.get("strategy")))
    await db.commit()
    return CrawlTaskAnalyzeResponse(task_id=task_id, status="completed", message=f"分析完成，共识别 {len(modules)} 个模块")

@router.get("/models")
async def get_available_models():
    models = [{"id": "deepseek", "name": "DeepSeek Chat", "type": "text", "description": "基于页面文本内容的竞品功能拆解"}]
    if settings.mimo_api_key:
        models.extend([{"id": "mimo", "name": "Xiaomi MiMo", "type": "multimodal", "description": "基于页面截图的视觉分析"}, {"id": "auto", "name": "自动选择", "type": "auto", "description": "优先使用 MiMo 截图分析，失败自动降级 DeepSeek"}])
    return {"models": models}

@router.get("/screenshots/{page_id}")
async def get_page_screenshot(page_id: str, db: AsyncSession = Depends(get_db)):
    page = (await db.execute(select(CrawledPage).where(CrawledPage.id == page_id))).scalar_one_or_none()
    if not page: raise HTTPException(status_code=404, detail="页面不存在")
    sp = (page.extra_meta or {}).get("screenshot_path")
    if not sp or not os.path.exists(sp): raise HTTPException(status_code=404, detail="截图不存在")
    return {"page_id": page_id, "base64": ScreenshotService.to_base64(sp), "filename": os.path.basename(sp)}
