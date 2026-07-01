"""导出服务"""
import json

class ExportService:
    @staticmethod
    async def generate_reverse_prd(project_name: str, modules: list[dict], industry: str = None, description: str = None) -> str:
        import datetime
        lines = [f"# 逆向PRD：{project_name}", "", f"> 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "", "---", ""]
        if description: lines.extend(["## 项目背景", "", description, ""])
        if industry: lines.append(f"- **所属行业**：{industry}\n")
        lines.extend(["## 功能架构总览", ""])
        for mod in modules:
            lines.append(f"- **{mod.get('name','')}**")
            for page in mod.get("pages",[]): lines.append(f"  - {page.get('name','')}（{len(page.get('features',[]))}个功能点）")
        lines.extend(["", "---", ""])
        for i, mod in enumerate(modules, 1):
            lines.append(f"## 3.{i} 模块：{mod.get('name','')}"); lines.append("")
            if mod.get("description"): lines.extend([mod["description"], ""])
            for page in mod.get("pages",[]):
                lines.append(f"### 页面：{page.get('name','')}"); lines.append("")
                lines.append("| 功能名称 | 功能描述 | 交互类型 | 输入 | 输出 | 约束条件 |"); lines.append("|---------|---------|---------|-----|-----|---------|")
                for feat in page.get("features",[]):
                    lines.append(f"| {feat.get('name','')} | {feat.get('description','')} | {feat.get('type','')} | {feat.get('inputs','')} | {feat.get('outputs','')} | {feat.get('constraints','')} |")
                lines.append("")
        lines.extend(["---", "", "*本文档由 AI 竞品逆向分析工具自动生成*"])
        return "\n".join(lines)

    @staticmethod
    async def generate_comparison_report(base_name: str, competitors: list[dict], summary: str) -> str:
        import datetime
        lines = [f"# 竞品功能对比报告", "", f"> 基准产品：**{base_name}**\n> 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "", "---", ""]
        if summary: lines.extend(["## 对比总结", "", summary, "", "---", ""])
        for comp in competitors:
            lines.append(f"## 与 {comp['name']} 对比"); lines.append("")
            if comp.get("summary"): lines.extend([f">{comp['summary']}", ""])
            lines.append("| 功能点 | 匹配状态 | 竞品功能 | 说明 |"); lines.append("|--------|---------|---------|------|")
            for feat_id, match_data in comp.get("alignment_matrix",{}).items():
                for c_name, m_info in match_data.items():
                    mt = m_info.get("match_type","none")
                    icon = {"exact":"✓ 完全匹配","similar":"~ 近似匹配","partial":"◐ 部分匹配","none":"✗ 不匹配"}
                    lines.append(f"| {m_info.get('base_feature_name',feat_id[:8])} | {icon.get(mt,mt)} | {m_info.get('matched_name','-')} | {m_info.get('note','')} |")
            lines.append("")
        lines.extend(["---", "", "*本文档由 AI 竞品逆向分析工具自动生成*"])
        return "\n".join(lines)

    @staticmethod
    async def generate_feature_matrix(modules: list[dict]) -> str:
        import datetime
        lines = ["# 功能清单矩阵", "", f"> 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
        for mod in modules:
            lines.append(f"## {mod.get('name','')}"); lines.append("")
            lines.append("| 页面 | 功能名称 | 功能描述 | 类型 | 来源 |"); lines.append("|------|---------|---------|------|------|")
            for page in mod.get("pages",[]):
                for feat in page.get("features",[]):
                    conf = feat.get("confidence_score",0)
                    lines.append(f"| {page.get('name','')} | {feat.get('name','')} | {feat.get('description','')} | {feat.get('type','')} | {'AI识别' if conf>=0.7 else 'AI识别（低置信度）'} |")
            lines.append("")
        return "\n".join(lines)
