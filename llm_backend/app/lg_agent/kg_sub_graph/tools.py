"""工具 Schema 定义"""
from pydantic import BaseModel, Field


class predefined_cypher(BaseModel):
    """【快】向量匹配预定义查询，直接执行，适合 90% 常见问题。
    支持：产品/价格筛选、订单查询、物流追踪、评价查询、员工管理等。
    当问题明确、可归类时优先使用此工具。"""
    query: str = Field(..., description="匹配到的预定义查询名称")
    parameters: dict = Field(default_factory=dict, description="查询参数")


class cypher_query(BaseModel):
    """【准】LLM 动态生成 Cypher 查询，适合复杂/自定义问题。
    根据 Neo4j Schema 和 few-shot 示例动态生成查询语句，
    经过语法校验后执行。当预定义查询无法覆盖时使用此工具。"""
    task: str = Field(..., description="用户的原始问题")
