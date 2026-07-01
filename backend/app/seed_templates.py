"""种子模板初始化脚本"""
from sqlalchemy import select
from app.database import get_db
from app.models.analysis import AnalysisTemplate
import asyncio

TEMPLATE_BACKEND = {
    "template_name": "B端后台模板", "template_type": "b端后台",
    "description": "适用于企业管理后台、CRM、ERP等B端系统",
    "dimensions": {"feature_extraction": {"enabled": True, "detail_level": "high", "include_buttons": True, "include_forms": True, "include_tables": True, "include_filters": True, "include_batch_ops": True}, "business_flow": {"enabled": True, "auto_detect_start_end": True, "max_flows": 5}, "permission_analysis": {"enabled": True, "roles_to_analyze": ["admin", "user", "viewer"]}, "field_analysis": {"enabled": True, "extract_validation": True, "extract_data_type": True}, "acceptance_criteria": {"enabled": True, "style": "gherkin"}},
    "is_system": True,
}

TEMPLATE_CONSUMER = {
    "template_name": "C端产品模板", "template_type": "c端产品",
    "description": "适用于电商、社交、内容平台等C端产品",
    "dimensions": {"feature_extraction": {"enabled": True, "detail_level": "medium", "include_buttons": True, "include_forms": True, "include_tables": False, "include_filters": True, "include_batch_ops": False}, "business_flow": {"enabled": True, "auto_detect_start_end": True, "max_flows": 3}},
    "is_system": True,
}

TEMPLATE_SAAS = {
    "template_name": "SaaS协作工具模板", "template_type": "saas",
    "description": "适用于项目管理、文档协作、在线办公等SaaS工具",
    "dimensions": {"feature_extraction": {"enabled": True, "detail_level": "high", "include_buttons": True, "include_forms": True, "include_tables": True, "include_filters": True, "include_batch_ops": True}, "business_flow": {"enabled": True, "auto_detect_start_end": True, "max_flows": 4}, "permission_analysis": {"enabled": True, "roles_to_analyze": ["owner", "admin", "member", "viewer"]}},
    "is_system": True,
}

async def seed_templates():
    db_gen = get_db(); db = await db_gen.__anext__()
    try:
        for template_data in [TEMPLATE_BACKEND, TEMPLATE_CONSUMER, TEMPLATE_SAAS]:
            result = await db.execute(select(AnalysisTemplate).where(AnalysisTemplate.template_name == template_data["template_name"], AnalysisTemplate.is_system == True))
            existing = result.scalar_one_or_none()
            if existing:
                for key, value in template_data.items(): setattr(existing, key, value)
                print(f"  [UPDATE] 模板已更新: {template_data['template_name']}")
            else:
                db.add(AnalysisTemplate(template_name=template_data["template_name"], template_type=template_data["template_type"], description=template_data["description"], dimensions=template_data["dimensions"], prompt_template="", placeholder_vars={"site_name": "竞品名称", "industry": "行业类型", "page_count": "页面数量", "pages_content": "页面内容"}, is_system=True, usage_count=0))
                print(f"  [CREATE] 创建模板: {template_data['template_name']}")
        await db.commit()
        print("  [OK] 种子模板初始化完成")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(seed_templates())
