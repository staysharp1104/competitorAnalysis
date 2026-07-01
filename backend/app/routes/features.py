from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.feature import FeatureNode
from app.models.project import Project
from app.schemas import FeatureNodeCreate, FeatureNodeUpdate, FeatureNodeResponse

router = APIRouter(prefix="/api/features", tags=["features"])

def _build_tree(nodes: list[FeatureNode], parent_id: str | None = None) -> list[dict]:
    tree = []
    for node in nodes:
        if node.parent_id == parent_id:
            node_dict = node.to_dict()
            node_dict["children"] = _build_tree(nodes, node.id)
            tree.append(node_dict)
    tree.sort(key=lambda x: x["sort_order"])
    return tree

@router.post("", response_model=FeatureNodeResponse)
async def create_feature_node(data: FeatureNodeCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Project).where(Project.id == data.project_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none(): raise HTTPException(status_code=404, detail="项目不存在")
    node = FeatureNode(project_id=data.project_id, parent_id=data.parent_id, level=data.level, node_type=data.node_type, name=data.name, description=data.description, source_page_id=data.source_page_id, source_type=data.source_type, tags=data.tags, constraints=data.constraints, validation_rules=data.validation_rules, acceptance_criteria=data.acceptance_criteria, confidence_score=data.confidence_score)
    db.add(node); await db.commit(); await db.refresh(node)
    return node.to_dict()

@router.get("/tree/{project_id}", response_model=list[FeatureNodeResponse])
async def get_feature_tree(project_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(FeatureNode).where(FeatureNode.project_id == project_id, FeatureNode.status != "deprecated").order_by(FeatureNode.sort_order)
    result = await db.execute(stmt)
    return _build_tree(result.scalars().all())

@router.get("/{node_id}", response_model=FeatureNodeResponse)
async def get_feature_node(node_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(FeatureNode).where(FeatureNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node: raise HTTPException(status_code=404, detail="功能节点不存在")
    node_dict = node.to_dict(); node_dict["children"] = []
    return node_dict

@router.put("/{node_id}", response_model=FeatureNodeResponse)
async def update_feature_node(node_id: str, data: FeatureNodeUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(FeatureNode).where(FeatureNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node: raise HTTPException(status_code=404, detail="功能节点不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None: setattr(node, key, value)
    await db.commit(); await db.refresh(node)
    return node.to_dict()

@router.delete("/{node_id}")
async def delete_feature_node(node_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(FeatureNode).where(FeatureNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node: raise HTTPException(status_code=404, detail="功能节点不存在")
    node.status = "deprecated"
    await db.commit()
    return {"message": "删除成功"}

@router.patch("/{node_id}/move")
async def move_feature_node(node_id: str, parent_id: str | None = None, sort_order: int = 0, db: AsyncSession = Depends(get_db)):
    stmt = select(FeatureNode).where(FeatureNode.id == node_id)
    result = await db.execute(stmt)
    node = result.scalar_one_or_none()
    if not node: raise HTTPException(status_code=404, detail="功能节点不存在")
    node.parent_id = parent_id; node.sort_order = sort_order
    await db.commit()
    return {"message": "移动成功"}
