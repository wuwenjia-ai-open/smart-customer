"""工具 Pydantic Schema 定义 — 用于 LLM bind_tools()"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ── 新工具 ──

class semantic_search(BaseModel):
    """【语义搜索】根据用户需求场景描述在产品知识库中语义搜索匹配产品。
    适用：用户描述需求但不知道具体产品名，如"适合小户型的智能门锁"。"""
    query: str = Field(..., description="用户需求场景的自然语言描述，不是产品名")
    top_k: int = Field(default=5, description="返回结果数量")


class compare_products(BaseModel):
    """【产品对比】并排对比两个或多个产品的价格、功能、评价。
    适用：用户问"A和B哪个好"、"帮我对比一下"。"""
    product_names: List[str] = Field(..., min_length=2, max_length=5, description="要对比的产品名称列表")
    aspects: Optional[List[str]] = Field(default=None, description="对比维度，如['价格','功能','评价']，不传则全维度")


class recommend(BaseModel):
    """【产品推荐】根据用户画像、预算和场景推荐产品。
    适用："预算2000想买扫地机器人"、"送父母的智能音箱推荐"。"""
    scenario: str = Field(..., description="使用场景描述")
    budget_min: Optional[float] = Field(default=None, description="预算下限")
    budget_max: Optional[float] = Field(default=None, description="预算上限")
    preferences: Optional[List[str]] = Field(default=None, description="偏好标签，如['安静','大容量','节能']")
    exclude: Optional[List[str]] = Field(default=None, description="排除的产品名")
    top_k: int = Field(default=3, description="推荐数量")


class track_shipment(BaseModel):
    """【订单查询】凭订单号查订单的全部信息 — 下单时间 / 发货时间 / 收件人 / 商品明细 / 物流状态。
    适用:任何形如"查订单 #1001"、"我的订单到哪了"、"订单详情"、"发货了吗"、"几号下的单"等问题。
    **只要有订单号就调这个**,不要因为用户提到"详情"二字就以为没有合适工具。"""
    order_id: int = Field(..., description="订单号(从用户消息中提取,例如 '订单 #1001' 中提取 1001)")


class create_ticket(BaseModel):
    """【创建工单】为用户创建售后工单。
    适用：用户明确要求退货/换货/维修，且 FAQ 无法解决。"""
    issue_type: Literal["退货", "换货", "维修", "投诉", "其他"] = Field(..., description="工单类型")
    order_id: Optional[int] = Field(default=None, description="关联订单号")
    description: str = Field(..., description="问题描述")
    priority: Literal["normal", "urgent"] = Field(default="normal", description="优先级")


class ask_clarification(BaseModel):
    """【澄清提问】当任务信息不足时，向用户提出精准的澄清问题。
    此工具不执行查询，调用后 Worker 将暂停并等待用户回应。

    两种使用方式：
    1. 澄清（默认）：用户问题属于本 Worker 领域，但缺少必要参数（如缺订单号、缺产品名）。
       只填 question 和 missing_field，**不要**填 reroute_to。
    2. 转路由：用户问题**根本不属于**本 Worker 领域（如 product_qa 收到「怎么退货」），
       此时填 reroute_to=<目标 worker>，让 Supervisor 重新分发。"""
    question: str = Field(..., description="向用户提出的澄清问题，单句，不超过30字")
    missing_field: str = Field(..., description="缺失的关键字段，如'order_id','product_name'")
    options: Optional[List[str]] = Field(default=None, description="可选澄清选项")
    reroute_to: Optional[str] = Field(
        default=None,
        description=(
            "仅当用户问题本质不属于当前 Worker 领域时填写（如 product_qa 收到售后退货问题）。"
            "**重要**：如果问题属于本 Worker 但只是缺参数（如 order_qa 缺订单号、product_qa 缺产品名），"
            "必须留空——只通过 question 索取信息即可。"
            "可选值: product_qa | order_qa | after_sales | general_chat"
        ),
    )


class escalate_to_human(BaseModel):
    """【转人工】将当前会话转接给人工客服。
    适用：用户明确要求人工、投诉升级、工具无法解决的问题。"""
    reason: str = Field(..., description="转接原因")
    summary: str = Field(..., description="问题摘要，供人工客服快速了解上下文")
    urgency: Literal["normal", "urgent", "critical"] = Field(default="normal", description="紧急程度")


class search_faq(BaseModel):
    """【FAQ搜索】在知识库中搜索常见问题答案。
    适用："退货流程是什么"、"保修多久"、"怎么开发票" 等政策类问题。"""
    keyword: str = Field(..., description="搜索关键词，如'退货'、'保修'、'配送'、'发票'")


