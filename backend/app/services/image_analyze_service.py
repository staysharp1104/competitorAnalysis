"""图片 AI 分析服务"""
import os, base64, asyncio
from io import BytesIO
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.services.ai_analyzer import AIAnalyzer
from app.services.feature_node_service import FeatureNodeService
from app.models.project_image import ProjectImage
from app.models.feature import FeatureNode

MAX_IMAGE_WIDTH = 1200; MIMO_TIMEOUT = 60.0

class ImageAnalyzeService:
    def __init__(self, analyzer: AIAnalyzer): self.analyzer = analyzer

    @staticmethod
    def _resize_image_base64(filepath: str, max_width: int = MAX_IMAGE_WIDTH) -> str:
        from PIL import Image
        img = Image.open(filepath)
        if img.mode not in ("RGB","L"): img = img.convert("RGB")
        if img.width > max_width:
            ratio = max_width/img.width
            img = img.resize((max_width, int(img.height*ratio)), Image.LANCZOS)
        buf = BytesIO(); img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    async def analyze_project_images(self, db: AsyncSession, project_id: str, image_ids: Optional[list[str]] = None) -> dict:
        stmt = select(ProjectImage).where(ProjectImage.project_id == project_id, ProjectImage.status.in_(["pending","failed"]))
        if image_ids: stmt = stmt.where(ProjectImage.id.in_(image_ids))
        stmt = stmt.order_by(ProjectImage.sort_order)
        result = await db.execute(stmt); images = result.scalars().all()
        if not images: return {"status":"failed","message":"没有待分析的图片","module_count":0,"feature_count":0}
        for img in images: img.status = "processing"
        await db.commit()
        extracted_pages = []; failed_count = 0
        SHARED_PROMPT = "请以专业产品经理的视角分析这个页面的截图。输出严格的JSON格式，包含module、page_name、features字段。"
        for img in images:
            try:
                if not os.path.exists(img.file_path): img.status = "failed"; img.error_msg = "文件不存在"; failed_count += 1; continue
                b64 = self._resize_image_base64(img.file_path)
                result_data = None; strategy = ""
                if self.analyzer.doubao_client:
                    dr = await self.analyzer.doubao_client.analyze_screenshot(image_base64=b64, page_title=img.file_name, prompt_text=SHARED_PROMPT, timeout=90)
                    if dr.get("features"): result_data = dr; strategy = "image_doubao"
                if not strategy and self.analyzer.mimo_client:
                    mr = await self.analyzer.mimo_client.analyze_screenshot(image_base64=b64, page_title=img.file_name, prompt_text=SHARED_PROMPT)
                    if mr.get("features"): result_data = mr; strategy = "image_mimo"
                if not strategy:
                    result_data = {"module":"未归类","page_name":img.file_name,"features":[{"name":f"{os.path.splitext(img.file_name)[0]}页面","description":"基于文件名生成的占位","type":"data_display","inputs":"","outputs":"","constraints":"","confidence_score":0.2}]}
                    strategy = "image_fallback"
                extracted_pages.append({"page_id":img.id,"page_title":result_data.get("page_name","") or img.file_name,"module":result_data.get("module","未归类") or "未归类","features":result_data.get("features",[]),"strategy":strategy})
                img.status = "completed"
            except Exception as e: img.status = "failed"; img.error_msg = str(e)[:200]; failed_count += 1
        await db.commit()
        if not extracted_pages: return {"status":"failed","message":f"所有图片分析失败（{failed_count}张）","module_count":0,"feature_count":0}
        if len(extracted_pages) > 1:
            try:
                aggregated = await self.analyzer.aggregate_features(pages_data=extracted_pages, site_name=project_id)
                modules = aggregated.get("modules",[])
            except: modules = []
            if not modules:
                mm = {}
                for p in extracted_pages:
                    mn = p.get("module","未归类")
                    if mn not in mm: mm[mn] = []
                    mm[mn].append(p)
                modules = [{"name":mn,"description":"","pages":[{"name":pp["page_title"],"description":"","features":pp["features"],"strategy":pp.get("strategy","image_mimo")} for pp in pages]} for mn,pages in mm.items()]
        else:
            pr = extracted_pages[0]
            modules = [{"name":pr.get("module","未归类"),"description":"","pages":[{"name":pr["page_title"],"description":"","features":pr["features"],"strategy":pr.get("strategy","image_mimo")}]}]
        stats = await FeatureNodeService.bulk_create_from_analysis(db=db, project_id=project_id, modules=modules)
        return {"status":"completed","message":f"分析完成：识别 {stats['module_count']} 个模块，{stats['feature_count']} 个功能点", "module_count":stats["module_count"], "feature_count":stats["feature_count"]}
