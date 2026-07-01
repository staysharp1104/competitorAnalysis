"""图片上传存储服务"""
import os, uuid
from typing import Optional
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.project import Project

ALLOWED_EXTENSIONS = {".jpg",".jpeg",".png",".webp"}
MAX_FILE_SIZE = 10*1024*1024
MAX_FILE_COUNT = 30

class ImageStorage:
    @staticmethod
    def validate_files(files: list[UploadFile]) -> list[dict]:
        if len(files) > MAX_FILE_COUNT: raise HTTPException(status_code=400, detail=f"最多上传{MAX_FILE_COUNT}张图片")
        results = []
        for i, f in enumerate(files):
            ext = os.path.splitext(f.filename or "")[1].lower()
            results.append({"index": i, "filename": f.filename or f"image_{i}", "error": None if ext in ALLOWED_EXTENSIONS else f"不支持格式: {ext}"})
        return results

    @staticmethod
    async def save_file(file: UploadFile, project_id: str, image_id: str) -> str:
        ext = os.path.splitext(file.filename or ".png")[1].lower()
        if ext not in ALLOWED_EXTENSIONS: ext = ".png"
        save_dir = os.path.join(settings.upload_dir, "project_images", project_id)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, f"{image_id}{ext}")
        content = await file.read()
        if len(content) > MAX_FILE_SIZE: raise HTTPException(status_code=400, detail=f"文件过大")
        with open(filepath, "wb") as f: f.write(content)
        return filepath

    @staticmethod
    async def auto_create_project(db: AsyncSession, project_name: Optional[str] = None) -> Project:
        from datetime import datetime, timezone
        name = project_name or f"图片拆解-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        project = Project(id=str(uuid.uuid4()), name=name, description="通过图片上传创建的AI拆解项目", project_type="single", status="active")
        db.add(project); await db.commit(); await db.refresh(project)
        return project
