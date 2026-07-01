from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.post("", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(name=data.name, description=data.description, product_line=data.product_line, industry=data.industry, project_type=data.project_type)
    db.add(project); await db.commit(); await db.refresh(project)
    return project.to_dict()

@router.get("", response_model=list[ProjectResponse])
async def list_projects(status: str = "active", db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.status == status).order_by(Project.updated_at.desc())
    result = await db.execute(stmt)
    return [p.to_dict() for p in result.scalars().all()]

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")
    return project.to_dict()

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None: setattr(project, key, value)
    await db.commit(); await db.refresh(project)
    return project.to_dict()

@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")
    project.status = "deleted"
    await db.commit()
    return {"message": "删除成功"}
