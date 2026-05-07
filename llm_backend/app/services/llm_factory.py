from app.core.config import settings
from app.services.deepseek_service import DeepseekService


class LLMFactory:
    @staticmethod
    def create_chat_service():
        return DeepseekService()

    @staticmethod
    def create_agent_llm(temperature: float = 0.7):
        """创建 Agent 节点使用的 LLM，统一管理参数"""
        from langchain_deepseek import ChatDeepSeek
        return ChatDeepSeek(
            api_key=settings.DEEPSEEK_API_KEY,
            model_name=settings.DEEPSEEK_MODEL,
            temperature=temperature,
        )
