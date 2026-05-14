"""LangGraph Agent 查询路由"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
import os
import json

from app.core.logger import get_logger
from app.core.config import settings
from app.lg_agent.lg_states import InputState
from app.lg_agent.utils import new_uuid
from app.lg_agent.lg_builder import supervisor_graph as graph
from langgraph.types import Command

router = APIRouter()
logger = get_logger(service="langgraph")


class LangGraphResumeRequest(BaseModel):
    query: str
    user_id: int
    conversation_id: str


@router.post("/langgraph/query")
async def langgraph_query(
    query: str = Form(...),
    user_id: int = Form(...),
    conversation_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    try:
        logger.info(f"LangGraph query user={user_id} conv={conversation_id}")

        image_path = None
        if image:
            image_dir = Path("uploads/images")
            image_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name, ext = os.path.splitext(image.filename)
            new_filename = f"{original_name}_{timestamp}{ext}"
            image_path = image_dir / new_filename
            content = await image.read()
            with open(image_path, "wb") as f:
                f.write(content)
            logger.info(f"Saved image {new_filename} for user {user_id}")

        is_new = not conversation_id
        thread_id = conversation_id if conversation_id else new_uuid()
        thread_config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
                "image_path": str(image_path) if image_path else None,
            }
        }

        async def process_stream():
            # 新会话同步到 MySQL（不影响 Agent 流程）
            if is_new:
                try:
                    from app.services.conversation_service import ConversationService
                    await ConversationService.create_conversation(
                        user_id=user_id, title=query[:30], thread_id=thread_id
                    )
                except Exception:
                    logger.warning(f"Failed to create conversation record for thread {thread_id}, proceeding without persistence")
            yield f"data: {json.dumps({'status': 'thinking', 'msg': '对方正在输入...'})}\n\n"
            try:
                stream_input = InputState(messages=query)
                result = await graph.ainvoke(stream_input, thread_config)
                # 优先取 messages，其次取 answer
                answer = ""
                msgs = result.get("messages", [])
                if msgs:
                    last = msgs[-1]
                    content = getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else None)
                    if content:
                        answer = str(content)
                if not answer:
                    answer = str(result.get("answer", "") or result.get("summary", ""))
                if answer:
                    for i in range(0, len(answer), 32):
                        yield f"data: {json.dumps(answer[i:i+32], ensure_ascii=False)}\n\n"
                    return
                yield f"data: {json.dumps('抱歉，我暂时无法回答这个问题，请稍后再试或换个问法～')}\n\n"
            except Exception:
                logger.exception("Agent error")
                yield f"data: {json.dumps('系统开小差了，请稍后再试～')}\n\n"

        response = StreamingResponse(process_stream(), media_type="text/event-stream")
        response.headers["X-Conversation-ID"] = thread_id
        return response

    except Exception as e:
        logger.error(f"LangGraph query error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/langgraph/resume")
async def langgraph_resume(request: LangGraphResumeRequest):
    try:
        logger.info(f"Resuming LangGraph user={request.user_id} conv={request.conversation_id}")
        thread_config = {"configurable": {"thread_id": request.conversation_id}}

        async def process_resume():
            async for c, metadata in graph.astream(
                Command(resume=request.query), stream_mode="messages", config=thread_config
            ):
                if c.content and not c.additional_kwargs.get("tool_calls"):
                    yield f"data: {json.dumps(c.content, ensure_ascii=False)}\n\n"
                elif c.additional_kwargs.get("tool_calls"):
                    tool_data = c.additional_kwargs.get("tool_calls")[0]["function"].get("arguments")
                    logger.debug(f"Tool call: {tool_data}")

        return StreamingResponse(process_resume(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"LangGraph resume error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
