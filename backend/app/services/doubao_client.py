"""火山引擎 ARK（豆包）多模态模型客户端"""
import json, re, httpx
from typing import Optional

class DoubaoClient:
    def __init__(self, api_key: str, base_url: str = "https://ark.cn-beijing.volces.com/api/v3", model: str = ""):
        self.api_key = api_key; self.base_url = base_url.rstrip("/"); self.model = model

    async def analyze_screenshot(self, image_base64: str, page_title: str, prompt_text: str, max_tokens: int = 4096, temperature: float = 0.3, timeout: float = 90.0) -> dict:
        payload = {"model": self.model or "doubao-vision", "messages": [{"role": "system", "content": "你是竞品分析专家。输出严格的JSON格式。"}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}, {"type": "text", "text": prompt_text}]}], "max_tokens": max_tokens, "temperature": temperature}
        async with httpx.AsyncClient(timeout=timeout+10.0) as client:
            try:
                resp = await client.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json=payload)
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return self._parse_json_response(content)
            except: return {"module": "", "page_name": page_title, "features": []}

    def _parse_json_response(self, response: str) -> dict:
        try: return self._normalize_page_obj(json.loads(response))
        except: pass
        jm = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if jm:
            try: return self._normalize_page_obj(json.loads(jm.group(1)))
            except: pass
        for m in re.finditer(r"\{(?:[^{}]|\{[^{}]*\})*\}", response):
            try: return self._normalize_page_obj(json.loads(m.group(0)))
            except: continue
        return {"module": "解析错误", "page_name": "", "features": []}

    @staticmethod
    def _normalize_page_obj(obj: dict) -> dict:
        cn_map = {"模块":"module","模块名称":"module","页面":"page_name","页面名称":"page_name","功能点":"features","功能列表":"features"}
        for cn_key, en_key in cn_map.items():
            if cn_key in obj and en_key not in obj: obj[en_key] = obj.pop(cn_key)
        if "features" not in obj: obj["features"] = []
        if "module" not in obj: obj["module"] = "未归类"
        for f in obj["features"]:
            for k in ("inputs","outputs","constraints"):
                if k not in f: f[k] = ""
                elif isinstance(f[k], list): f[k] = "；".join(str(x) for x in f[k] if x)
            if "confidence_score" not in f: f["confidence_score"] = 0.7
        return obj
