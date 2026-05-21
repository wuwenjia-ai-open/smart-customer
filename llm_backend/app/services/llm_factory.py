"""LLM 工厂 — 三档分层路由

tier 说明：
  flash  → DeepSeek V4-Flash   主力 (classify/decompose/merge/product_qa/general_chat)
  tool   → GPT-5.4 Mini        工具调用专用 (order_qa)
  reason → GPT-5.5             推理专用 (after_sales)
"""
from app.core.config import settings
from app.services.deepseek_service import DeepseekService


class LLMFactory:
    @staticmethod
    def create_chat_service():
        return DeepseekService()

    @staticmethod
    def create_llm(tier: str = "flash"):
        """按档位创建 LLM 实例

        Args:
            tier: "flash" | "tool" | "reason"
        """
        if tier == "flash":
            from langchain_deepseek import ChatDeepSeek
            return ChatDeepSeek(
                api_key=settings.DEEPSEEK_API_KEY,
                model_name=settings.DEEPSEEK_MODEL,
                temperature=0.3,
            )

        if tier == "tool":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=settings.GPT_API_KEY,
                base_url=settings.GPT_BASE_URL,
                model=settings.GPT_TOOL_MODEL,
                temperature=0.1,  # 工具调用要高确定性
            )

        if tier == "reason":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                api_key=settings.GPT_API_KEY,
                base_url=settings.GPT_BASE_URL,
                model=settings.GPT_REASON_MODEL,
                temperature=0.5,  # 推理+同理心保留创造性
            )

        raise ValueError(f"Unknown LLM tier: {tier!r}, must be 'flash' | 'tool' | 'reason'")

    # 向后兼容旧调用
    @staticmethod
    def create_agent_llm(temperature: float = 0.7):
        return LLMFactory.create_llm("flash")
