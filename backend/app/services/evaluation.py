"""评测脚本"""
import json, os
from app.services.ai_analyzer import AIAnalyzer

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "fixtures", "evaluation_dataset.json")

def load_dataset() -> dict:
    with open(DATASET_PATH, "r", encoding="utf-8") as f: return json.load(f)

class Evaluator:
    def __init__(self): self.analyzer = AIAnalyzer()

    def calculate_recall(self, predicted: list[dict], ground_truth: list[dict]) -> float:
        predicted_names = {f["name"] for f in predicted}
        truth_names = {f["name"] for f in ground_truth}
        if not truth_names: return 0.0
        return len(predicted_names & truth_names) / len(truth_names)

    def calculate_precision(self, predicted: list[dict], ground_truth: list[dict]) -> float:
        predicted_names = {f["name"] for f in predicted}
        truth_names = {f["name"] for f in ground_truth}
        if not predicted_names: return 0.0
        return len(predicted_names & truth_names) / len(predicted_names)

    def calculate_hallucination_rate(self, predicted: list[dict], ground_truth: list[dict]) -> float:
        predicted_names = {f["name"] for f in predicted}
        truth_names = {f["name"] for f in ground_truth}
        if not predicted_names: return 0.0
        return len(predicted_names - truth_names) / len(predicted_names)

    def check_format_compliance(self, result: dict) -> bool:
        if not isinstance(result, dict): return False
        if "module" not in result and "modules" not in result: return False
        return True

    async def evaluate_site(self, site_data: dict) -> dict:
        page_stats = []; total_recall = total_precision = total_hallucination = 0.0
        for page in site_data["pages"]:
            page_name = page["page_name"]; gt = page["ground_truth"]
            result = await self.analyzer.extract_features_from_page(page_title=page_name, page_content=self._build_mock_page_content(page), site_name=site_data["site_name"], industry=site_data.get("industry","互联网"))
            predicted_features = result.get("features",[])
            recall = self.calculate_recall(predicted_features, gt["features"])
            precision = self.calculate_precision(predicted_features, gt["features"])
            hallucination = self.calculate_hallucination_rate(predicted_features, gt["features"])
            total_recall += recall; total_precision += precision; total_hallucination += hallucination
            page_stats.append({"page_name": page_name, "gt_count": len(gt["features"]), "predicted_count": len(predicted_features), "recall": round(recall,3), "precision": round(precision,3), "hallucination_rate": round(hallucination,3), "format_compliant": self.check_format_compliance(result)})
        count = len(page_stats) or 1
        return {"site_name": site_data["site_name"], "page_count": len(site_data["pages"]), "avg_recall": round(total_recall/count,3), "avg_precision": round(total_precision/count,3), "avg_hallucination": round(total_hallucination/count,3), "pages": page_stats}

    def _build_mock_page_content(self, page: dict) -> str:
        parts = [f"# {page['page_name']}\n"]
        for feat in page["ground_truth"]["features"]:
            parts.extend([f"- {feat['name']}：{feat['description']}", f"  - 类型：{feat['type']}", f"  - 输入：{feat['inputs']}", f"  - 输出：{feat['outputs']}", ""])
        return "\n".join(parts)

    async def evaluate_all(self) -> dict:
        dataset = load_dataset(); results = []
        for site in dataset["sites"]: results.append(await self.evaluate_site(site))
        count = len(results) or 1
        return {"version": dataset["version"], "total_sites": len(results), "overall_recall": round(sum(r["avg_recall"] for r in results)/count,3), "overall_precision": round(sum(r["avg_precision"] for r in results)/count,3), "overall_hallucination": round(sum(r["avg_hallucination"] for r in results)/count,3), "sites": results}
