"""图片上传与AI拆解路由"""
import os, uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.models.project_image import ProjectImage
from app.services.image_storage import ImageStorage
from app.services.image_analyze_service import ImageAnalyzeService
from app.services.ai_analyzer import AIAnalyzer
from app.models.feature import FeatureNode

router = APIRouter(prefix="/api/images", tags=["images"])
ai_analyzer = AIAnalyzer()
image_analyze_service = ImageAnalyzeService(ai_analyzer)

class AnalyzeRequest(BaseModel):
    image_ids: Optional[list[str]] = None

@router.post("/upload")
async def upload_images(project_id: str = Form(None), files: list[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    validation = ImageStorage.validate_files(files)
    errors = [v for v in validation if v["error"]]
    if errors:
        raise HTTPException(status_code=400, detail=f"部分文件格式不支持: {', '.join(e['filename'] for e in errors)}")
    if project_id:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project: raise HTTPException(status_code=404, detail="项目不存在")
    else:
        project = await ImageStorage.auto_create_project(db)
    created_images = []
    for i, file in enumerate(files):
        img_id = str(uuid.uuid4())
        filepath = await ImageStorage.save_file(file, project.id, img_id)
        image = ProjectImage(id=img_id, project_id=project.id, file_name=file.filename or f"image_{i}", file_path=filepath, file_size=0, sort_order=i, status="pending")
        db.add(image); await db.flush(); await db.refresh(image)
        if os.path.exists(filepath): image.file_size = os.path.getsize(filepath)
        created_images.append(image.to_dict())
    await db.commit()
    return {"project_id": project.id, "images": created_images}

@router.post("/{project_id}/analyze")
async def analyze_images(project_id: str, req: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none(): raise HTTPException(status_code=404, detail="项目不存在")
    return await image_analyze_service.analyze_project_images(db=db, project_id=project_id, image_ids=req.image_ids)

@router.get("/{project_id}/result")
async def get_analysis_result(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FeatureNode).where(FeatureNode.project_id == project_id, FeatureNode.parent_id.is_(None)).order_by(FeatureNode.sort_order))
    root_nodes = result.scalars().all()
    tree = []
    for node in root_nodes:
        children_result = await db.execute(select(FeatureNode).where(FeatureNode.parent_id == node.id).order_by(FeatureNode.sort_order))
        children = children_result.scalars().all()
        nd = node.to_dict(); nd["children"] = [c.to_dict() for c in children]; tree.append(nd)
    return {"status": "completed" if tree else "no_data", "modules": tree}

@router.get("/project/{project_id}")
async def list_project_images(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectImage).where(ProjectImage.project_id == project_id).order_by(ProjectImage.sort_order))
    return [img.to_dict() for img in result.scalars().all()]

@router.get("/project/{project_id}/file/{image_id}")
async def serve_image_file(project_id: str, image_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectImage).where(ProjectImage.id == image_id, ProjectImage.project_id == project_id))
    image = result.scalar_one_or_none()
    if not image: raise HTTPException(status_code=404, detail="图片不存在")
    if not os.path.exists(image.file_path): raise HTTPException(status_code=404, detail="图片文件已丢失")
    return FileResponse(image.file_path, media_type="image/jpeg")
