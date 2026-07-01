from fastapi import APIRouter
router = APIRouter(prefix="/api/export", tags=["export"])
@router.get("/health")
async def export_health():
    return {"status": "ok", "message": "导出服务运行中"}
