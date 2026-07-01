import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.models.page import CrawledPage
from app.models.feature import FeatureNode
from app.models.analysis import AnalysisReport
from app.services.ai_analyzer import AIAnalyzer
from app.services.export_service import ExportService
from app.schemas import AnalyzeRequest, AnalyzeResponse, ReportGenerateRequest, ReportResponse

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
ai_analyzer = AIAnalyzer()
export_service = ExportService()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_pages(data: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == data.project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")

    pages_stmt = select(CrawledPage).where(CrawledPage.id.in_(data.page_ids))
    pages_result = await db.execute(pages_stmt)
    pages = pages_result.scalars().all()
    if not pages: raise HTTPException(status_code=400, detail="未找到指定页面")

    pages_data = [{"id": p.id, "title": p.title, "clean_content": p.clean_content or p.raw_content or ""} for p in pages]
    result_data = await ai_analyzer.analyze_pages(pages=pages_data, site_name=project.name, industry=project.industry or "")

    modules = result_data.get("modules", [])
    module_sort = 0
    feature_count = 0
    for mod in modules:
        module_sort += 1
        module_node = FeatureNode(project_id=data.project_id, parent_id=None, sort_order=module_sort, level=1, node_type="module", name=mod.get("name", "未命名模块"), description=mod.get("description", ""), source_type="auto", confidence_score=0.85)
        db.add(module_node); await db.flush(); await db.refresh(module_node)
        page_sort = 0
        for page_data in mod.get("pages", []):
            page_sort += 1
            page_node = FeatureNode(project_id=data.project_id, parent_id=module_node.id, sort_order=page_sort, level=2, node_type="page", name=page_data.get("name", "未命名页面"), description=page_data.get("description", ""), source_type="auto", confidence_score=0.85)
            db.add(page_node); await db.flush(); await db.refresh(page_node)
            feat_sort = 0
            for feat in page_data.get("features", []):
                feat_sort += 1; feature_count += 1
                db.add(FeatureNode(project_id=data.project_id, parent_id=page_node.id, sort_order=feat_sort, level=3, node_type="feature", name=feat.get("name", "未命名功能"), description=feat.get("description", ""), source_type="auto", constraints=feat.get("constraints", ""), confidence_score=feat.get("confidence_score", 0.7)))
    await db.commit()
    return AnalyzeResponse(task_id=data.project_id, status="completed", message=f"分析完成，共识别 {len(modules)} 个模块，{feature_count} 个功能点")

@router.post("/generate-report", response_model=ReportResponse)
async def generate_report(data: ReportGenerateRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == data.project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project: raise HTTPException(status_code=404, detail="项目不存在")

    feat_stmt = select(FeatureNode).where(FeatureNode.project_id == data.project_id, FeatureNode.status != "deprecated").order_by(FeatureNode.sort_order)
    feat_result = await db.execute(feat_stmt)
    feature_nodes = feat_result.scalars().all()

    modules = []
    for node in feature_nodes:
        if node.level == 1:
            modules.append({"id": node.id, "name": node.name, "description": node.description or "", "pages": []})
        elif node.level == 2 and modules:
            modules[-1]["pages"].append({"id": node.id, "name": node.name, "description": node.description or "", "features": []})
        elif node.level == 3 and modules and modules[-1]["pages"]:
            modules[-1]["pages"][-1]["features"].append({"name": node.name, "description": node.description or "", "type": "feature", "inputs": "", "outputs": "", "constraints": node.constraints or "", "confidence_score": float(node.confidence_score) if node.confidence_score else 0})

    if data.report_type == "reverse_prd":
        content = await export_service.generate_reverse_prd(project_name=project.name, modules=modules, industry=project.industry, description=project.description)
    elif data.report_type == "feature_matrix":
        content = await export_service.generate_feature_matrix(modules)
    else:
        content = json.dumps(modules, ensure_ascii=False, indent=2)

    report = AnalysisReport(project_id=data.project_id, report_name=f"{project.name} - 逆向PRD", report_type=data.report_type, export_format=data.export_format, content=content, status="completed")
    db.add(report); await db.commit(); await db.refresh(report)
    return report.to_dict()

@router.get("/reports/{project_id}", response_model=list[ReportResponse])
async def list_reports(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AnalysisReport).where(AnalysisReport.project_id == project_id).order_by(AnalysisReport.created_at.desc())
    result = await db.execute(stmt)
    return [r.to_dict() for r in result.scalars().all()]

@router.get("/reports/detail/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(AnalysisReport).where(AnalysisReport.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    if not report: raise HTTPException(status_code=404, detail="报告不存在")
    return report.to_dict()
