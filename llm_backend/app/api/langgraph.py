"""LangGraph Agent 查询路由 — 支持流式输出"""
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

from app.core.logger import get_logger
from app.core.config import settings
from app.lg_agent.lg_states import InputState
from app.lg_agent.utils import new_uuid
from app.lg_agent.lg_builder import get_graph
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
):
    try:
        logger.info(f"LangGraph query user={user_id} conv={conversation_id}")

        is_new = not conversation_id
        thread_id = conversation_id if conversation_id else new_uuid()
        thread_config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
            }
        }

        async def process_stream():
            # 新会话同步到 MySQL
            if is_new:
                try:
                    from app.services.conversation_service import ConversationService
                    await ConversationService.create_conversation(
                        user_id=user_id, title=query[:30], thread_id=thread_id
                    )
                except Exception:
                    logger.warning(
                        f"Failed to create conversation record for thread {thread_id}, "
                        "proceeding without persistence"
                    )

            yield f"data: {json.dumps({'status': 'thinking', 'msg': '正在分析您的问题...'})}\n\n"

            try:
                stream_input = InputState(messages=query)
                graph = await get_graph()

                last_status = None
                inside_final_node = False  # 是否在 merge_results / respond 内部
                chunks_emitted = False  # 是否已经流式输出过文本（用于快速通道兜底判断）
                async for event in graph.astream_events(stream_input, thread_config, version="v2"):
                    kind = event.get("event", "")
                    node_name = event.get("name", "")

                    # 追踪当前链
                    if kind == "on_chain_start":
                        status_map = {
                            "classify_intent": "正在理解您的问题...",
                            "decompose_tasks": "正在分析任务...",
                            "dispatch_workers": "正在分发任务给专家...",
                            "product_qa": "正在查询商品信息...",
                            "order_qa": "正在查询订单信息...",
                            "after_sales": "正在处理售后请求...",
                            "general_chat": "正在准备回复...",
                            "merge_results": "正在整理回答...",
                        }
                        status_msg = status_map.get(node_name)
                        if status_msg and status_msg != last_status:
                            last_status = status_msg
                            yield f"data: {json.dumps({'status': 'progress', 'msg': status_msg})}\n\n"
                        if node_name in ("merge_results", "respond"):
                            inside_final_node = True

                    elif kind == "on_chain_end":
                        if node_name == "merge_results":
                            inside_final_node = False
                        elif node_name == "respond":
                            inside_final_node = False
                            # 单结果快速通道：merge_results 直接给出 final_answer，
                            # respond_node 只是封装为 AIMessage，没有 LLM 调用，
                            # 因此前面没有任何 on_chat_model_stream 事件。
                            # 在 respond 结束时兜底把答案切片推给前端。
                            if not chunks_emitted:
                                output = event.get("data", {}).get("output") or {}
                                msgs = output.get("messages") if isinstance(output, dict) else None
                                if msgs:
                                    content = getattr(msgs[-1], "content", "") or ""
                                    if content:
                                        for i in range(0, len(content), 8):
                                            yield f"data: {json.dumps(content[i:i+8], ensure_ascii=False)}\n\n"

                    # LLM token 流式输出 — 只推最终回答节点
                    if kind == "on_chat_model_stream" and inside_final_node:
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            chunks_emitted = True
                            yield f"data: {json.dumps(chunk.content, ensure_ascii=False)}\n\n"

                yield f"data: {json.dumps({'status': 'done'})}\n\n"

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
            graph = await get_graph()
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
