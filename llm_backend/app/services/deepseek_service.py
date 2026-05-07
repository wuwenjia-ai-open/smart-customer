from typing import List, Dict, AsyncGenerator, Callable, Optional
from openai import AsyncOpenAI
from app.core.config import settings
import json
from app.core.logger import get_logger
from app.core.database import AsyncSessionLocal
from app.models.message import Message
import time

logger = get_logger(service="deepseek")

class DeepseekService:
    def __init__(self, model: str = "deepseek-chat"):
        logger.info(f"Deepseek Service initialized: model={settings.DEEPSEEK_MODEL}")
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.DEEPSEEK_MODEL or model

    async def generate_stream(
        self,
        messages: List[Dict],
        user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        on_complete: Optional[Callable[[int, int, List[Dict], str], None]] = None
    ) -> AsyncGenerator[str, None]:
        """流式生成回复"""
        try:
            start_time = time.time()

            full_response = []
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = json.dumps(chunk.choices[0].delta.content, ensure_ascii=False)
                    full_response.append(content)
                    yield f"data: {content}\n\n"

            complete_response = "".join(full_response)
            response_time = time.time() - start_time
            logger.info(f"Response time: {response_time:.4f} seconds")

            if on_complete and user_id is not None and conversation_id is not None:
                await on_complete(user_id, conversation_id, messages, complete_response)

        except Exception as e:
            err_str = str(e).replace("{", "{{").replace("}", "}}")
            logger.error("Error in generate_stream: {}", err_str)
            error_msg = json.dumps(f"生成回复时出错: {str(e)}", ensure_ascii=False)
            yield f"data: {error_msg}\n\n"

    async def generate(self, messages: List[Dict]) -> str:
        """非流式生成回复"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Generation error: {str(e)}")
            raise 