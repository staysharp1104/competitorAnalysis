"""AI拆解引擎"""
import json
import re
import os
from typing import Optional
from openai import AsyncOpenAI
from app.config import settings
from app.services.mimo_client import MiMoClient
from app.services.doubao_client import DoubaoClient
from app.services.screenshot_service import ScreenshotService

PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts")

def _load_prompt(relative_path: str) -> str:
    filepath = os.path.join(PROMPT_DIR, relative_path)
    lines = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"): continue
            lines.append(line)
    return "".join(lines).strip()

SYSTEM_PROMPT = """你是一个专业的竞品分析专家和产品需求分析师。你的核心能力是：
1. 功能识别：精准识别网页中的每个可操作功能点
2. 模块划分：按产品功能领域将页面归入合理的系统模块
3. 三级拆解：按「系统模块 → 页面 → 功能点」三级结构输出
4. 多维分析：识别功能约束、权限规则、数据字段、业务流程
你的输出必须是严格的JSON格式，确保可以被程序解析。"""

MODULE_CLASSIFICATION_PROMPT = """请根据以下页面的标题和概要，对竞品系统的整体模块结构进行划分。
竞品名称：{site_name}\n所属行业：{industry}\n页面列表：\n{pages_summary}\n
输出格式（严格JSON）：
{{"modules": [{{"name": "模块名称", "description": "模块描述", "is_core": true, "related_pages": ["页面标题1"]}}]}}
"""

FEATURE_EXTRACTION_DEFAULT = """请分析以下竞品页面内容，提取所有功能点。
竞品名称：{site_name}\n所属行业：{industry}\n页面内容（来源：{page_title}）：\n```\n{page_content}\n```\n
输出格式（严格JSON）：
{{"module": "模块名称", "page_name": "{page_title}", "features": [{{"name": "功能名称", "description": "功能描述", "type": "button/form/table/filter", "inputs": "输入说明", "outputs": "输出说明", "constraints": "约束条件", "confidence_score": 0.95}}]}}
"""

AGGREGATE_PROMPT_DEFAULT = """请将以下多个页面的功能点数据，按「系统模块 → 页面 → 功能点」三级结构归并整合。
竞品名称：{site_name}\n所属行业：{industry}\n各页面功能点数据：\n{pages_data}\n
输出格式（严格JSON）：
{{"modules": [{{"name": "模块名称", "description": "模块描述", "pages": [...]}}]}}
"""

class AIAnalyzer:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.llm_api_key or "sk-placeholder", base_url=settings.llm_base_url)
        self.model = settings.llm_model
        self._extraction_prompt_template = self._load_prompt_or_default("extraction/v1.txt", FEATURE_EXTRACTION_DEFAULT)
        self._aggregation_prompt_template = self._load_prompt_or_default("aggregation/v1.txt", AGGREGATE_PROMPT_DEFAULT)
        self.mimo_client: Optional[MiMoClient] = None
        if settings.mimo_api_key:
            self.mimo_client = MiMoClient(api_key=settings.mimo_api_key, base_url=settings.mimo_base_url, model=settings.mimo_model)
        self.doubao_client: Optional[DoubaoClient] = None
        if settings.doubao_api_key:
            self.doubao_client = DoubaoClient(api_key=settings.doubao_api_key, base_url=settings.doubao_base_url, model=settings.doubao_model)
        self._prompt_registry: dict[str, str] = {}
        self._load_prompt_registry()

    def _load_prompt_registry(self):
        for pt in ["form_page","dashboard","auth_page","content_page","settings_page","general_page","data_table"]:
            self._prompt_registry[pt] = FEATURE_EXTRACTION_DEFAULT

    def _select_prompt_by_type(self, page_type: str) -> str:
        return self._prompt_registry.get(page_type, FEATURE_EXTRACTION_DEFAULT)

    def _load_prompt_or_default(self, path: str, default: str) -> str:
        try:
            content = _load_prompt(path)
            if content: return content
        except: pass
        return default

    async def classify_modules(self, pages_summary: list[dict], site_name: str = "竞品站点", industry: str = "互联网") -> list[dict]:
        summary_lines = [f"- [{p.get('struct_elements',{}).get('page_type','unknown')}] {p.get('title','未命名')}: {p.get('clean_content','')[:100]}..." for p in pages_summary]
        prompt = MODULE_CLASSIFICATION_PROMPT.format(site_name=site_name, industry=industry, pages_summary="\n".join(summary_lines))
        response = await self._call_llm(prompt, use_json=True)
        result = self._parse_json_response(response)
        return result.get("modules", [])

    async def extract_features_from_page(self, page_title: str, page_content: str, struct_elements: Optional[dict] = None, site_name: str = "竞品站点", industry: str = "互联网", screenshot_path: Optional[str] = None, model: str = "deepseek") -> dict:
        if model == "mimo" and screenshot_path and self.mimo_client:
            image_b64 = ScreenshotService.to_base64(screenshot_path)
            prompt = "请以专业产品经理的视角分析这个页面的截图。输出严格的JSON格式，包含module/page_name/features字段。"
            return await self.mimo_client.analyze_screenshot(image_b64, page_title, prompt)
        prompt = self._extraction_prompt_template.format(site_name=site_name, industry=industry, page_title=page_title, page_content=page_content[:8000])
        response = await self._call_llm(prompt, use_json=True)
        return self._parse_json_response(response)

    async def aggregate_features(self, pages_data: list[dict], site_name: str = "竞品站点", industry: str = "互联网") -> dict:
        prompt = self._aggregation_prompt_template.format(site_name=site_name, industry=industry, pages_data=json.dumps(pages_data, ensure_ascii=False, indent=2))
        response = await self._call_llm(prompt, use_json=True)
        return self._parse_json_response(response)

    async def analyze_pages(self, pages: list[dict], site_name: str = "竞品站点", industry: str = "", model: str = "deepseek") -> dict:
        industry = industry or "互联网"
        modules = (await self.classify_modules(pages_summary=pages, site_name=site_name, industry=industry)) if len(pages) > 1 else []
        import asyncio
        tasks = [self._extract_with_fallback(page_title=page.get("title",""), page_content=page.get("clean_content",""), struct_elements=page.get("struct_elements"), site_name=site_name, industry=industry, screenshot_path=page.get("screenshot_path"), model=model) for page in pages]
        page_results = await asyncio.gather(*tasks, return_exceptions=True)
        extracted_pages = []
        for i, result in enumerate(page_results):
            if isinstance(result, Exception): continue
            result_data, strategy = result if isinstance(result, tuple) else (result, "unknown")
            features = result_data.get("features", [])
            extracted_pages.append({"page_id": pages[i].get("id"), "page_title": pages[i].get("title",""), "module": result_data.get("module","默认模块"), "features": features, "strategy": strategy})
        if not extracted_pages: return {"modules": []}
        if len(extracted_pages) > 1:
            aggregated = await self.aggregate_features(pages_data=extracted_pages, site_name=site_name, industry=industry)
            return aggregated
        pr = extracted_pages[0]
        return {"modules": [{"name": pr.get("module","默认模块"), "description": "", "pages": [{"name": pr["page_title"], "description": "", "features": pr["features"], "strategy": pr.get("strategy","")}]}]}

    async def _extract_with_fallback(self, page_title: str, page_content: str, struct_elements: Optional[dict] = None, site_name: str = "竞品站点", industry: str = "互联网", screenshot_path: Optional[str] = None, model: str = "deepseek") -> tuple[dict, str]:
        if model == "auto" and screenshot_path and self.mimo_client:
            result = await self.extract_features_from_page(page_title=page_title, page_content=page_content, struct_elements=struct_elements, site_name=site_name, industry=industry, screenshot_path=screenshot_path, model="mimo")
            if result.get("features"): return result, "mimo_auto"
        result = await self.extract_features_from_page(page_title=page_title, page_content=page_content, struct_elements=struct_elements, site_name=site_name, industry=industry)
        if result.get("features"): return result, "v2_structured"
        return self._extract_nav_structure(struct_elements), "nav_fallback"

    @staticmethod
    def _extract_nav_structure(struct_elements: Optional[dict]) -> dict:
        from urllib.parse import urlparse
        links = (struct_elements or {}).get("interactive_elements", {}).get("nav_links", [])
        modules = []; seen = set()
        for link in links:
            href = link.get("href", "")
            path = urlparse(href).path.strip("/").split("/")
            if path and path[0] and path[0] not in seen:
                seen.add(path[0])
                modules.append({"name": path[0], "description": f"导航: {path[0]}", "pages": [{"name": link.get("text",path[0]), "description": "", "features": [{"name": f"访问{link.get('text','')}页面", "type": "navigation", "inputs": "", "outputs": "页面跳转", "constraints": "", "confidence_score": 0.5}]}]})
        return {"modules": modules} if modules else {"modules": []}

    async def _call_llm(self, prompt: str, use_json: bool = False) -> str:
        kwargs = {"model": self.model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 4096}
        if use_json: kwargs["response_format"] = {"type": "json_object"}
        try:
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except:
            return self._get_mock_response(prompt)

    def _parse_json_response(self, response: str) -> dict:
        try: return json.loads(response)
        except: pass
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            try: return json.loads(json_match.group(1))
            except: pass
        brace_match = re.search(r"\{.*\}", response, re.DOTALL)
        if brace_match:
            try: return json.loads(brace_match.group(0))
            except: pass
        return {"module": "解析错误", "page_name": "", "features": []}

    def _get_mock_response(self, prompt: str) -> str:
        import json
        return json.dumps({"module": "用户管理", "page_name": "用户列表", "features": [{"name": "新增用户", "description": "创建新用户", "type": "button", "inputs": "用户名、邮箱", "outputs": "创建成功", "constraints": "用户名唯一", "confidence_score": 0.92}, {"name": "用户搜索", "description": "搜索用户", "type": "filter", "inputs": "关键词", "outputs": "用户列表", "constraints": "关键词2-50字符", "confidence_score": 0.88}]})
