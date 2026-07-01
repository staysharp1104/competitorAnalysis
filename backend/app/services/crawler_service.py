"""全站爬取服务"""
import json, re, asyncio, sys, os
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Optional
from bs4 import BeautifulSoup
import trafilatura
from markdownify import markdownify as md
import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.crawler import CrawlTask
from app.models.page import CrawledPage, PageContent
from app.services.html_struct_extractor import HtmlStructExtractor
from app.services.screenshot_service import ScreenshotService
from app.config import settings

class CrawlerService:
    EXCLUDED_EXTENSIONS = {".pdf",".zip",".rar",".gz",".tar",".jpg",".png",".gif",".svg",".ico",".css",".js",".mp4",".mp3",".doc",".docx",".xls",".xlsx",".ppt",".pptx"}
    DEFAULT_EXCLUDE_PATTERNS = ["/help/","/api/","/docs/","/swagger","/logout","/login","/register","/signup","/cdn-","/assets/","/static/","/images/"]

    @staticmethod
    def _normalize_url(url: str, base_url: str = "") -> str:
        if not url or url.startswith("#") or url.startswith("javascript:"): return ""
        if base_url and not url.startswith(("http://","https://")): url = urljoin(base_url, url)
        if not url.startswith(("http://","https://")): return ""
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))

    @staticmethod
    def _should_exclude(url: str, exclude_patterns: list[str]) -> bool:
        parsed = urlparse(url)
        for ext in CrawlerService.EXCLUDED_EXTENSIONS:
            if parsed.path.lower().endswith(ext): return True
        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern.lower() in url_lower: return True
        return False

    @staticmethod
    def _get_domain(url: str) -> str: return urlparse(url).netloc.lower()

    @staticmethod
    def _is_same_domain(url: str, domain: str) -> bool: return CrawlerService._get_domain(url) == domain

    @staticmethod
    def _extract_links(html: str, base_url: str, domain: str, exclude_patterns: list[str]) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        links = set()
        for a in soup.find_all("a", href=True):
            normalized = CrawlerService._normalize_url(a["href"].strip(), base_url)
            if normalized and CrawlerService._is_same_domain(normalized, domain) and not CrawlerService._should_exclude(normalized, exclude_patterns):
                links.add(normalized)
        return list(links)

    @staticmethod
    def _process_html(html: str, url: str = "") -> dict:
        clean_text = trafilatura.extract(html, include_links=True, include_images=False, include_tables=True, no_fallback=False, output_format="txt") or ""
        markdown_content = md(html, heading_style="ATX", strip=["script","style","nav","footer","aside"])
        struct_data = HtmlStructExtractor.extract_interactive_elements(html, url)
        return {"clean_text": clean_text, "markdown_content": markdown_content, "word_count": len(clean_text), "struct_elements": struct_data, "page_type": struct_data.get("page_type","general_page")}

    async def create_and_start_task(self, data, db: AsyncSession) -> CrawlTask:
        config = {}
        if data.exclude_patterns: config["exclude_patterns"] = data.exclude_patterns
        task = CrawlTask(project_id=data.project_id, root_url=data.root_url, status="pending", max_depth=data.max_depth, max_pages=data.max_pages, config=config if config else None)
        db.add(task); await db.commit(); await db.refresh(task)
        asyncio.create_task(self._run_crawl(task.id))
        return task

    async def _run_crawl(self, task_id: str):
        from app.database import async_session
        async with async_session() as db:
            try:
                result = await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))
                task = result.scalar_one_or_none()
                if not task: return
                task.status = "running"; await db.commit()
                exclude_patterns = list(CrawlerService.DEFAULT_EXCLUDE_PATTERNS)
                if task.config and task.config.get("exclude_patterns"):
                    exclude_patterns.extend(task.config["exclude_patterns"])
                domain = CrawlerService._get_domain(task.root_url)
                root_normalized = CrawlerService._normalize_url(task.root_url)
                queue = [(root_normalized, 0)]
                visited = {root_normalized}
                discovered = downloaded = filtered = failed = 0
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}) as client:
                    while queue:
                        task_check = await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))
                        task = task_check.scalar_one_or_none()
                        if not task or task.status == "cancelled": break
                        if task.status == "paused": await db.commit(); await asyncio.sleep(2); continue
                        current_url, depth = queue.pop(0)
                        try:
                            resp = await client.get(current_url)
                            discovered += 1
                            if resp.status_code != 200:
                                failed += 1
                                db.add(CrawledPage(project_id=task.project_id, crawl_task_id=task_id, url=current_url, page_depth=depth, http_status=resp.status_code, source_type="crawl"))
                                continue
                            html = resp.text; soup = BeautifulSoup(html, "lxml")
                            title = soup.title.string.strip() if soup.title else ""
                            if not title or "404" in title.lower(): filtered += 1; continue
                            processed = CrawlerService._process_html(html, current_url)
                            page = CrawledPage(project_id=task.project_id, crawl_task_id=task_id, title=title or current_url, url=current_url, page_depth=depth, http_status=resp.status_code, source_type="crawl", raw_content=processed["clean_text"], clean_content=processed["markdown_content"], extra_meta={"word_count": processed["word_count"], "page_type": processed["page_type"], "struct_elements": processed["struct_elements"]})
                            db.add(page); await db.flush(); await db.refresh(page)
                            db.add(PageContent(page_id=page.id, raw_html=html, markdown_content=processed["markdown_content"], word_count=processed["word_count"]))
                            downloaded += 1
                            if depth < task.max_depth and downloaded < task.max_pages:
                                for link in CrawlerService._extract_links(html, current_url, domain, exclude_patterns):
                                    if link not in visited: visited.add(link); queue.append((link, depth+1))
                        except: failed += 1
                        task.pages_discovered=discovered; task.pages_downloaded=downloaded; task.pages_filtered=filtered; task.pages_failed=failed
                        await db.commit()
                        if downloaded >= task.max_pages: break
                        await asyncio.sleep(1.5)
                task.status = "completed"; task.pages_discovered=discovered; task.pages_downloaded=downloaded; task.pages_filtered=filtered; task.pages_failed=failed
                await db.commit()
            except:
                try:
                    result = await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))
                    task = result.scalar_one_or_none()
                    if task: task.status = "failed"; await db.commit()
                except: pass

    @staticmethod
    async def pause_task(task_id: str, db: AsyncSession) -> bool:
        result = await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task or task.status != "running": return False
        task.status = "paused"; await db.commit(); return True

    @staticmethod
    async def resume_task(task_id: str, db: AsyncSession) -> bool:
        result = await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task or task.status != "paused": return False
        task.status = "running"; await db.commit(); return True

    @staticmethod
    async def cancel_task(task_id: str, db: AsyncSession) -> bool:
        result = await db.execute(select(CrawlTask).where(CrawlTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task or task.status in ("completed","failed","cancelled"): return False
        task.status = "cancelled"; await db.commit(); return True
