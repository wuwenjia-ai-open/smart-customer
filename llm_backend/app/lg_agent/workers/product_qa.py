"""ProductQA Worker — 产品查询/对比/推荐"""
from app.lg_agent.workers.react_loop import build_worker
from app.lg_agent.workers.tools.schemas import (
    semantic_search, compare_products, recommend,
    predefined_cypher, cypher_query, ask_clarification,
)
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的产品顾问。负责帮用户找到最合适的智能家居产品。

核心能力：语义搜索产品、横向对比价格功能评价、基于预算和场景做个性化推荐。

产品数据库覆盖：智能门锁、摄像头、音箱、扫地机器人、空调、灯具、窗帘、净水器、加湿器、电饭煲、洗衣机、冰箱、电视、马桶、体重秤、门铃、手环、空气净化器等 20+ 品类。"""

TOOLS = [semantic_search, compare_products, recommend, predefined_cypher, cypher_query, ask_clarification]


def build(llm):
    tool_descriptions = "\n".join(
        f"- **{t.__name__}**: {t.__doc__ or 'No description'}"
        for t in TOOLS
    )
    system_prompt = build_think_prompt("product_qa", tool_descriptions, identity=IDENTITY)
    return build_worker(llm, TOOLS, system_prompt, "product_qa")
