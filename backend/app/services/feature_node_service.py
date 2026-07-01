"""FeatureNode 批量创建服务"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.feature import FeatureNode

class FeatureNodeService:
    @staticmethod
    async def bulk_create_from_analysis(db: AsyncSession, project_id: str, modules: list[dict], strategy: str = "image_mimo", default_confidence: float = 0.85) -> dict:
        module_sort = 0; feature_count = 0
        for mod in modules:
            module_sort += 1
            module_node = FeatureNode(project_id=project_id, parent_id=None, sort_order=module_sort, level=1, node_type="module", name=mod.get("name","未命名模块"), description=mod.get("description",""), source_type="auto", confidence_score=default_confidence)
            db.add(module_node); await db.flush(); await db.refresh(module_node)
            page_sort = 0
            for page_data in mod.get("pages",[]):
                page_sort += 1
                page_node = FeatureNode(project_id=project_id, parent_id=module_node.id, sort_order=page_sort, level=2, node_type="page", name=page_data.get("name","未命名页面"), description=page_data.get("description",""), source_type="auto", confidence_score=default_confidence, strategy=page_data.get("strategy",strategy))
                db.add(page_node); await db.flush(); await db.refresh(page_node)
                feat_sort = 0
                for feat in page_data.get("features",[]):
                    feat_sort += 1; feature_count += 1
                    constraints_raw = feat.get("constraints","")
                    if isinstance(constraints_raw, list): constraints_raw = "；".join(str(x) for x in constraints_raw if x)
                    db.add(FeatureNode(project_id=project_id, parent_id=page_node.id, sort_order=feat_sort, level=3, node_type="feature", name=feat.get("name","未命名功能"), description=feat.get("description",""), source_type="auto", constraints=constraints_raw, confidence_score=feat.get("confidence_score",0.7)))
        await db.commit()
        return {"module_count": len(modules), "feature_count": feature_count}
