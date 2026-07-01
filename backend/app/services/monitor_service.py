"""监控服务"""
import traceback
from typing import Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.error_log import ErrorLog

class MonitorService:
    @staticmethod
    async def log_error(db: AsyncSession, message: str, level: str = "error", source: str = None, detail: str = None, path: str = None, method: str = None, project_id: str = None, status_code: int = None) -> ErrorLog:
        log = ErrorLog(level=level, source=source, message=str(message)[:500], detail=detail, path=path, method=method, project_id=project_id, status_code=status_code)
        db.add(log); await db.commit(); await db.refresh(log); return log

    @staticmethod
    async def log_exception(db: AsyncSession, exc: Exception, source: str = None, path: str = None, method: str = None, project_id: str = None) -> ErrorLog:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return await MonitorService.log_error(db=db, message=f"{type(exc).__name__}: {str(exc)}", level="error", source=source, detail=detail, path=path, method=method, project_id=project_id, status_code=500)

    @staticmethod
    async def list_errors(db: AsyncSession, level: str = None, source: str = None, project_id: str = None, days: int = None, page: int = 1, page_size: int = 20) -> tuple:
        query = select(ErrorLog); cq = select(func.count(ErrorLog.id))
        if level: query = query.where(ErrorLog.level == level); cq = cq.where(ErrorLog.level == level)
        if source: query = query.where(ErrorLog.source == source); cq = cq.where(ErrorLog.source == source)
        if project_id: query = query.where(ErrorLog.project_id == project_id); cq = cq.where(ErrorLog.project_id == project_id)
        if days: cutoff = datetime.now(timezone.utc) - timedelta(days=days); query = query.where(ErrorLog.created_at >= cutoff); cq = cq.where(ErrorLog.created_at >= cutoff)
        query = query.order_by(ErrorLog.created_at.desc()).offset((page-1)*page_size).limit(page_size)
        total = (await db.execute(cq)).scalar() or 0
        return list((await db.execute(query)).scalars().all()), total

    @staticmethod
    async def get_error(db: AsyncSession, error_id: str) -> Optional[ErrorLog]:
        return (await db.execute(select(ErrorLog).where(ErrorLog.id == error_id))).scalar_one_or_none()

    @staticmethod
    async def delete_error(db: AsyncSession, error_id: str) -> bool:
        log = (await db.execute(select(ErrorLog).where(ErrorLog.id == error_id))).scalar_one_or_none()
        if not log: return False
        await db.delete(log); await db.commit(); return True

    @staticmethod
    async def clear_errors(db: AsyncSession, days: int = None) -> int:
        query = delete(ErrorLog)
        if days: query = query.where(ErrorLog.created_at < datetime.now(timezone.utc) - timedelta(days=days))
        result = await db.execute(query); await db.commit()
        return result.rowcount

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        total = (await db.execute(select(func.count(ErrorLog.id)))).scalar() or 0
        today_start = datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
        today = (await db.execute(select(func.count(ErrorLog.id)).where(ErrorLog.created_at >= today_start))).scalar() or 0
        week = (await db.execute(select(func.count(ErrorLog.id)).where(ErrorLog.created_at >= datetime.now(timezone.utc)-timedelta(days=7)))).scalar() or 0
        levels = {}; sources = {}
        for row in await db.execute(select(ErrorLog.level,func.count(ErrorLog.id).label("cnt")).group_by(ErrorLog.level)): levels[row.level] = row.cnt
        for row in (await db.execute(select(ErrorLog.source,func.count(ErrorLog.id).label("cnt")).group_by(ErrorLog.source).order_by(func.count(ErrorLog.id).desc()).limit(10))).all():
            if row.source: sources[row.source] = row.cnt
        return {"total": total, "today": today, "week": week, "levels": levels, "sources": sources}
