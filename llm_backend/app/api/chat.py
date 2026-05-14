"""通用对话路由"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict
from app.services.llm_factory import LLMFactory
from app.services.conversation_service import ConversationService
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(service="chat")


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    user_id: int
    conversation_id: int


def _create_chat_stream(request: ChatRequest):
    chat_service = LLMFactory.create_chat_service()
    return StreamingResponse(
        chat_service.generate_stream(
            messages=request.messages,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            on_complete=ConversationService.save_message,
        ),
        media_type="text/event-stream",
    )


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"Chat request user={request.user_id} conv={request.conversation_id}")
        return _create_chat_stream(request)
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
