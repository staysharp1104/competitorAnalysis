"""小米 MiMo 多模态模型客户端"""
import json, re, httpx

class MiMoClient:
    def __init__(self, api_key: str, base_url: str = "https://api.xiaomimimo.com/v1", model: str = "mimo-v2.5"):
        self.api_key = api_key; self.base_url = base_url.rstrip("/"); self.model = model

    async def analyze_screenshot(self, image_base64: str, page_title: str, prompt_text: str, max_tokens: int = 4096, temperature: float = 0.3) -> dict:
        payload = {"model": self.model, "messages": [{"role": "system", "content": "你是竞品分析专家。输出严格的JSON格式。"}, {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}, {"type": "text", "text": prompt_text}]}], "max_completion_tokens": max_tokens, "temperature": temperature}
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(f"{self.base_url}/chat/completions", headers={"api-key": self.api_key, "Content-Type": "application/json"}, json=payload)
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                return self._parse_json_response(content)
            except: return {"module": "", "page_name": page_title, "features": []}

    def _parse_json_response(self, response: str) -> dict:
        def normalize(obj):
            cn_map = {"模块":"module","页面名称":"page_name","页面":"page_name","功能点":"features","功能列表":"features"}
            for k,v in list(obj.items()):
                nk = cn_map.get(k,k)
                if isinstance(v,dict): obj[nk] = normalize(v)
                elif isinstance(v,list): obj[nk] = [normalize(i) if isinstance(i,dict) else i for i in v]
                elif nk != k: obj[nk] = obj.pop(k)
            return obj
        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                all_features = []
                for item in parsed:
                    item = normalize(item)
                    all_features.extend(item.get("features",[]))
                return {"module": "", "page_name": "", "features": all_features}
            return normalize(parsed)
        except: pass
        jm = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if jm:
            try:
                parsed = json.loads(jm.group(1))
                return normalize(parsed)
            except: pass
        for m in re.finditer(r"\{(?:[^{}]|\{[^{}]*\})*\}", response):
            try: return normalize(json.loads(m.group(0)))
            except: continue
        return {"module": "解析错误", "page_name": "", "features": []}
