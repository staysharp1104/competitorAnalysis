import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.models.page import CrawledPage, PageContent
from app.schemas import PageCreate, PageUpdate, PageResponse
from app.services.content_processor import ContentProcessor
from app.config import settings

router = APIRouter(prefix="/api/pages", tags=["pages"])
processor = ContentProcessor()

@router.post("", response_model=PageResponse)
async def create_page(data: PageCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == data.project_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none(): raise HTTPException(status_code=404, detail="项目不存在")

    if data.html_content:
        processed = await processor.process_html(data.html_content)
        clean_content = processed["clean_text"]
    elif data.raw_content and data.source_type in ("paste", "text"):
        processed = await processor.process_plain_text(data.raw_content, data.title)
        clean_content = processed["clean_text"]
    else:
        clean_content = data.clean_content or ""

    sort_stmt = select(CrawledPage).where(CrawledPage.project_id == data.project_id, CrawledPage.parent_id == data.parent_id).order_by(CrawledPage.sort_order.desc())
    sort_result = await db.execute(sort_stmt)
    last_page = sort_result.scalars().first()
    next_sort = (last_page.sort_order + 1) if last_page else 0

    page = CrawledPage(project_id=data.project_id, parent_id=data.parent_id, title=data.title or "未命名页面", url=data.url, source_type=data.source_type, raw_content=data.raw_content or "", clean_content=clean_content, sort_order=next_sort)
    db.add(page); await db.commit(); await db.refresh(page)
    return page.to_dict()

@router.post("/upload")
async def upload_page_file(project_id: str = Form(...), title: str = Form(None), file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none(): raise HTTPException(status_code=404, detail="项目不存在")

    content = await file.read()
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext in (".html", ".htm"):
        processed = await processor.process_html(content.decode("utf-8", errors="replace"))
        source_type = "html"
    elif file_ext == ".pdf":
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content); tmp_path = tmp.name
        processed = await processor.process_pdf(tmp_path)
        os.unlink(tmp_path)
        source_type = "pdf"
    else:
        processed = await processor.process_plain_text(content.decode("utf-8", errors="replace"), title)
        source_type = "text"

    page = CrawledPage(project_id=project_id, title=title or (file.filename or "未命名页面"), source_type=source_type, raw_content=content.decode("utf-8", errors="replace")[:5000], clean_content=processed["clean_text"])
    db.add(page); await db.commit(); await db.refresh(page)
    return page.to_dict()

@router.get("/project/{project_id}", response_model=list[PageResponse])
async def list_project_pages(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CrawledPage).where(CrawledPage.project_id == project_id).order_by(CrawledPage.sort_order)
    result = await db.execute(stmt)
    return [p.to_dict() for p in result.scalars().all()]

@router.get("/{page_id}", response_model=PageResponse)
async def get_page(page_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CrawledPage).where(CrawledPage.id == page_id)
    result = await db.execute(stmt)
    page = result.scalar_one_or_none()
    if not page: raise HTTPException(status_code=404, detail="页面不存在")
    return page.to_dict()

@router.get("/{page_id}/content")
async def get_page_content(page_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(PageContent).where(PageContent.page_id == page_id)
    result = await db.execute(stmt)
    content = result.scalar_one_or_none()
    if not content: raise HTTPException(status_code=404, detail="页面内容不存在")
    return {"page_id": content.page_id, "markdown_content": content.markdown_content, "raw_html": content.raw_html, "word_count": content.word_count}

@router.put("/{page_id}", response_model=PageResponse)
async def update_page(page_id: str, data: PageUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(CrawledPage).where(CrawledPage.id == page_id)
    result = await db.execute(stmt)
    page = result.scalar_one_or_none()
    if not page: raise HTTPException(status_code=404, detail="页面不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None: setattr(page, key, value)
    if "raw_content" in data.model_dump(exclude_unset=True) and data.raw_content:
        processed = await processor.process_plain_text(data.raw_content, page.title)
        page.clean_content = processed["clean_text"]
    await db.commit(); await db.refresh(page)
    return page.to_dict()

@router.delete("/{page_id}")
async def delete_page(page_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CrawledPage).where(CrawledPage.id == page_id)
    result = await db.execute(stmt)
    page = result.scalar_one_or_none()
    if not page: raise HTTPException(status_code=404, detail="页面不存在")
    content_stmt = select(PageContent).where(PageContent.page_id == page_id)
    content_result = await db.execute(content_stmt)
    page_content = content_result.scalar_one_or_none()
    if page_content: await db.delete(page_content)
    await db.delete(page)
    await db.commit()
    return {"message": "删除成功"}
