"""Supervisor 任务拆解提示词"""

DECOMPOSE_SYSTEM_PROMPT = """你是任务拆解专家。用户问题需要多个 Worker 协作。拆解为独立的子任务。

规则：
- 每个子任务分配给一个 Worker
- 子任务描述要自包含，Worker 不需要回头看原始问题
- 保留关键约束（订单号、预算、品类等）
- 能并行的任务标记相同 priority（1=最高）

输出 JSON 数组：
[
  {{"worker_type": "order_qa", "description": "...", "context": {{"order_id": 12345}}, "priority": 1}},
  {{"worker_type": "product_qa", "description": "...", "context": {{}}, "priority": 1}}
]
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class DecomposeSubTask(BaseModel):
    worker_type: str = Field(description="product_qa | order_qa | after_sales | general_chat")
    description: str = Field(description="自包含的任务描述")
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1)


class DecomposeOutput(BaseModel):
    sub_tasks: List[DecomposeSubTask] = Field(description="子任务列表")
