"""监控路由 - 系统错误日志查询与管理"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.monitor_service import MonitorService

router = APIRouter(prefix="/api/monitor", tags=["监控管理"])

@router.get("/errors")
async def list_errors(level: str = Query(None), source: str = Query(None), project_id: str = Query(None), days: int = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    logs, total = await MonitorService.list_errors(db, level=level, source=source, project_id=project_id, days=days, page=page, page_size=page_size)
    return {"items": [log.to_dict() for log in logs], "total": total, "page": page, "page_size": page_size}

@router.get("/errors/{error_id}")
async def get_error(error_id: str, db: AsyncSession = Depends(get_db)):
    log = await MonitorService.get_error(db, error_id)
    if not log: raise HTTPException(status_code=404, detail="错误日志不存在")
    return log.to_dict()

@router.delete("/errors/{error_id}")
async def delete_error(error_id: str, db: AsyncSession = Depends(get_db)):
    if not await MonitorService.delete_error(db, error_id): raise HTTPException(status_code=404, detail="错误日志不存在")
    return {"message": "删除成功"}

@router.delete("/errors")
async def clear_errors(days: int = Query(None), db: AsyncSession = Depends(get_db)):
    count = await MonitorService.clear_errors(db, days=days)
    return {"message": f"已清理 {count} 条记录"}

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    return await MonitorService.get_stats(db)
