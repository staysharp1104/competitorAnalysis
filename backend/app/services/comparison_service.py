"""对比分析服务"""
import json, re
from typing import Optional
from openai import AsyncOpenAI
from app.config import settings

ALIGNMENT_PROMPT = """请对以下两个竞品的功能点进行对齐匹配分析。
基准产品：{base_name}\n竞品产品：{competitor_name}\n
基准功能点：{base_features}\n竞品功能点：{competitor_features}\n
输出格式（严格JSON）：
{{"alignment": [{{"base_feature_id": "", "base_feature_name": "", "match_type": "exact/similar/partial/none", "matched_competitor_feature_id": null, "matched_name": "", "confidence": 0.0, "note": ""}}], "summary": ""}}
"""

class ComparisonService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.llm_api_key or "sk-placeholder", base_url=settings.llm_base_url)
        self.model = settings.llm_model

    def normalize_name(self, name: str) -> str:
        n = name.lower().strip()
        for prefix in ["查看","浏览","新增","创建","编辑","修改","删除","批量","管理"]:
            n = re.sub(f"^{prefix}", "", n)
        return n.strip()

    def exact_match(self, base_features: list[dict], comp_features: list[dict]) -> dict:
        comp_by_name = {self.normalize_name(f.get("name","")): f for f in comp_features}
        match_map = {}
        for bf in base_features:
            bf_norm = self.normalize_name(bf.get("name",""))
            matched = comp_by_name.get(bf_norm)
            match_map[bf.get("id",bf.get("name",""))] = {"match_type": "exact" if matched else "none", "matched_id": matched.get("id") if matched else None, "matched_name": matched.get("name") if matched else None, "confidence": 0.95 if matched else 0}
        return match_map

    async def llm_align(self, base_name: str, competitor_name: str, base_features: list[dict], competitor_features: list[dict]) -> dict:
        base_str = json.dumps(base_features, ensure_ascii=False, indent=2)[:6000]
        comp_str = json.dumps(competitor_features, ensure_ascii=False, indent=2)[:6000]
        if not settings.llm_api_key or settings.llm_api_key == "sk-placeholder":
            return self._get_mock_alignment(base_features, competitor_features)
        try:
            response = await self.client.chat.completions.create(model=self.model, messages=[{"role": "system", "content": "你是一个竞品分析专家。"}, {"role": "user", "content": ALIGNMENT_PROMPT.format(base_name=base_name, competitor_name=competitor_name, base_features=base_str, competitor_features=comp_str)}], temperature=0.2, max_tokens=4096, response_format={"type": "json_object"})
            return json.loads(response.choices[0].message.content or "{}")
        except:
            return self._get_mock_alignment(base_features, competitor_features)

    def _get_mock_alignment(self, base_features, competitor_features):
        comp_by_name = {self.normalize_name(f.get("name","")): f for f in competitor_features}
        alignment = []
        for bf in base_features:
            matched = comp_by_name.get(self.normalize_name(bf.get("name","")))
            alignment.append({"base_feature_id": bf.get("id",bf.get("name","")), "base_feature_name": bf.get("name",""), "match_type": "exact" if matched else "none", "matched_competitor_feature_id": matched.get("id") if matched else None, "matched_name": matched.get("name") if matched else None, "confidence": 0.85 if matched else 0, "note": "名称匹配" if matched else "竞品未覆盖"})
        return {"alignment": alignment, "summary": f"共发现{len(alignment)}个功能点，{sum(1 for a in alignment if a['match_type']!='none')}个匹配"}

    async def align_features(self, base_name, competitor_name, base_features, competitor_features):
        exact_map = self.exact_match(base_features, competitor_features)
        llm_result = await self.llm_align(base_name, competitor_name, base_features, competitor_features)
        alignment = llm_result.get("alignment", [])
        matrix = {}
        for a in alignment:
            bf_id = a.get("base_feature_id")
            if bf_id:
                if bf_id in exact_map and exact_map[bf_id]["match_type"] == "exact":
                    matrix[bf_id] = {competitor_name: exact_map[bf_id]}
                else:
                    matrix[bf_id] = {competitor_name: a}
        return matrix, llm_result.get("summary","")

    async def compare_feature_trees(self, base_project_name, base_modules, competitor_projects):
        result = {"base_name": base_project_name, "competitors": [], "summary": ""}
        summaries = []
        for comp in competitor_projects:
            matrix, summary = await self.align_features(base_project_name, comp["name"], self._extract_all_features(base_modules), self._extract_all_features(comp.get("modules",[])))
            result["competitors"].append({"name": comp["name"], "project_id": comp.get("id"), "alignment_matrix": matrix, "summary": summary})
            summaries.append(summary)
        result["summary"] = "; ".join(summaries)
        return result

    def _extract_all_features(self, modules):
        features = []
        for mod in modules:
            for page in mod.get("pages",[]):
                for feat in page.get("features",[]):
                    feat["_module"] = mod["name"]; feat["_page"] = page["name"]; features.append(feat)
        return features
