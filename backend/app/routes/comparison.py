"""对比分析 API 路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.models.feature import FeatureNode
from app.models.comparison import ComparisonAnalysis
from app.services.comparison_service import ComparisonService
from app.schemas import ComparisonCreate, ComparisonResponse, AlignmentUpdate
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/comparison", tags=["comparison"])
comparison_service = ComparisonService()
export_service = ExportService()

def _build_modules_from_tree(nodes: list[FeatureNode]) -> list[dict]:
    modules = []
    for node in nodes:
        if node.level == 1:
            modules.append({"id": node.id, "name": node.name, "description": node.description or "", "pages": []})
        elif node.level == 2 and modules:
            modules[-1]["pages"].append({"id": node.id, "name": node.name, "description": node.description or "", "features": []})
        elif node.level == 3 and modules and modules[-1]["pages"]:
            modules[-1]["pages"][-1]["features"].append({"id": node.id, "name": node.name, "description": node.description or "", "type": "feature", "inputs": "", "outputs": "", "constraints": node.constraints or "", "confidence_score": float(node.confidence_score) if node.confidence_score else 0})
    return modules

@router.post("/create", response_model=ComparisonResponse)
async def create_comparison(data: ComparisonCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == data.project_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none(): raise HTTPException(status_code=404, detail="基准项目不存在")
    for cid in data.competitor_ids:
        stmt = select(Project).where(Project.id == cid)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none(): raise HTTPException(status_code=404, detail=f"竞品项目 {cid} 不存在")
    stmt = select(ComparisonAnalysis).where(ComparisonAnalysis.project_id == data.project_id)
    result = await db.execute(stmt)
    for comp in result.scalars().all():
        if set(comp.competitor_ids or []) == set(data.competitor_ids):
            return comp.to_dict()
    comparison = ComparisonAnalysis(project_id=data.project_id, name=data.name, competitor_ids=data.competitor_ids, status="pending")
    db.add(comparison); await db.commit(); await db.refresh(comparison)
    return comparison.to_dict()

@router.post("/{comparison_id}/align", response_model=ComparisonResponse)
async def run_alignment(comparison_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ComparisonAnalysis).where(ComparisonAnalysis.id == comparison_id)
    result = await db.execute(stmt)
    comparison = result.scalar_one_or_none()
    if not comparison: raise HTTPException(status_code=404, detail="对比分析不存在")
    comparison.status = "aligning"
    await db.commit()
    try:
        feat_stmt = select(FeatureNode).where(FeatureNode.project_id == comparison.project_id, FeatureNode.status != "deprecated").order_by(FeatureNode.sort_order)
        feat_result = await db.execute(feat_stmt)
        base_modules = _build_modules_from_tree(feat_result.scalars().all())
        proj_result = await db.execute(select(Project).where(Project.id == comparison.project_id))
        base_project = proj_result.scalar_one()
        competitor_projects = []
        for cid in (comparison.competitor_ids or []):
            c_result = await db.execute(select(Project).where(Project.id == cid))
            c_project = c_result.scalar_one_or_none()
            if not c_project: continue
            cf_result = await db.execute(select(FeatureNode).where(FeatureNode.project_id == cid, FeatureNode.status != "deprecated").order_by(FeatureNode.sort_order))
            c_modules = _build_modules_from_tree(cf_result.scalars().all())
            competitor_projects.append({"id": cid, "name": c_project.name, "modules": c_modules})
        align_result = await comparison_service.compare_feature_trees(base_project_name=base_project.name, base_modules=base_modules, competitor_projects=competitor_projects)
        matrix = {}
        for comp in align_result.get("competitors", []):
            for feat_id, match_data in comp.get("alignment_matrix", {}).items():
                if feat_id not in matrix: matrix[feat_id] = {}
                matrix[feat_id][comp["name"]] = match_data
        comparison.alignment_matrix = matrix
        comparison.alignment_suggestions = align_result
        comparison.summary = align_result.get("summary", "")
        comparison.status = "completed"
        comparison.summary_content = await export_service.generate_comparison_report(base_name=base_project.name, competitors=align_result.get("competitors", []), summary=align_result.get("summary", ""))
        await db.commit(); await db.refresh(comparison)
        return comparison.to_dict()
    except Exception as e:
        comparison.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"对齐分析失败: {str(e)}")

@router.get("/{comparison_id}", response_model=ComparisonResponse)
async def get_comparison(comparison_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ComparisonAnalysis).where(ComparisonAnalysis.id == comparison_id)
    result = await db.execute(stmt)
    comparison = result.scalar_one_or_none()
    if not comparison: raise HTTPException(status_code=404, detail="对比分析不存在")
    return comparison.to_dict()

@router.put("/{comparison_id}/alignment", response_model=ComparisonResponse)
async def update_alignment(comparison_id: str, data: AlignmentUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(ComparisonAnalysis).where(ComparisonAnalysis.id == comparison_id)
    result = await db.execute(stmt)
    comparison = result.scalar_one_or_none()
    if not comparison: raise HTTPException(status_code=404, detail="对比分析不存在")
    comparison.alignment_matrix = data.alignment_matrix
    comparison.status = "completed"
    await db.commit(); await db.refresh(comparison)
    return comparison.to_dict()

@router.get("/list/{project_id}", response_model=list[ComparisonResponse])
async def list_comparisons(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ComparisonAnalysis).where(ComparisonAnalysis.project_id == project_id).order_by(ComparisonAnalysis.created_at.desc())
    result = await db.execute(stmt)
    return [c.to_dict() for c in result.scalars().all()]
