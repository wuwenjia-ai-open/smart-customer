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
            },
            "metadata": {
                "user_id": str(user_id),
                "thread_id": thread_id,
            },
            "tags": [f"user:{user_id}"],
            "run_name": f"query/{thread_id[:8]}",
        }

        async def process_stream():
            # 确保 Conversation 记录存在 — 自愈机制:
            #   - 全新会话 (is_new=True) 总是创建
            #   - 老 thread_id 但 DB 找不到 (前端 localStorage 与 DB 不同步) 也创建
            try:
                from app.services.conversation_service import ConversationService
                from app.core.database import AsyncSessionLocal
                from app.models.conversation import Conversation
                from sqlalchemy import select

                async with AsyncSessionLocal() as db:
                    existing = (await db.execute(
                        select(Conversation).where(Conversation.thread_id == thread_id)
                    )).scalar_one_or_none()

                if not existing:
                    await ConversationService.create_conversation(
                        user_id=user_id, title=query[:30], thread_id=thread_id
                    )
                    logger.info(f"Conversation auto-created for thread {thread_id} (is_new={is_new})")
            except Exception:
                logger.exception(
                    f"Failed to ensure conversation record for thread {thread_id}, "
                    "proceeding without persistence"
                )

            yield f"data: {json.dumps({'status': 'thinking', 'msg': '正在分析您的问题...'})}\n\n"

            assistant_buffer = []  # accumulates full answer for save_message_pair

            try:
                stream_input = InputState(messages=query)
                graph = await get_graph()

                last_status = None
                chunks_emitted = False  # 是否已经流式输出过文本（用于快速通道兜底判断）

                # 这些节点的 LLM token 才允许流式输出到前端。
                # Worker (product_qa/order_qa/after_sales/general_chat) 的 LLM
                # 可能违反 prompt 输出"用户咨询..."前缀,虽然 worker 会剥掉后传给
                # merge,但流式 token 已经通过 astream_events 发出 — 必须在 SSE
                # 这一层就过滤,否则前端会看到 worker 的内部输出和 merge 的真实
                # 回复字符级交错。
                STREAMING_NODES = {"merge_results"}  # respond 无 LLM 调用

                async for event in graph.astream_events(stream_input, thread_config, version="v2"):
                    kind = event.get("event", "")
                    node_name = event.get("name", "")
                    # langgraph_node 标识事件来自哪个图节点 — 比依赖累积的
                    # inside_final_node 标志更稳 (后者会被嵌套子图的 on_chain_start
                    # 误置位)
                    event_node = (event.get("metadata") or {}).get("langgraph_node", "")

                    # 状态进度提示
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

                    # respond 节点结束时,如果整轮还没流过任何 token (fast-path
                    # 走的就是这条 — merge 不调 LLM 直接 set final_answer),
                    # 把 final AIMessage 内容分块推给前端。
                    # 每块加小延时,否则一次性全 flush,前端看着是一坨而不是流式。
                    elif kind == "on_chain_end" and node_name == "respond":
                        if not chunks_emitted:
                            output = event.get("data", {}).get("output") or {}
                            msgs = output.get("messages") if isinstance(output, dict) else None
                            if msgs:
                                content = getattr(msgs[-1], "content", "") or ""
                                if content:
                                    assistant_buffer.append(content)
                                    import asyncio as _asyncio
                                    CHUNK_SIZE = 2
                                    CHUNK_DELAY = 0.025  # 25ms / chunk, ~80 字/秒
                                    for i in range(0, len(content), CHUNK_SIZE):
                                        piece = content[i:i + CHUNK_SIZE]
                                        yield f"data: {json.dumps(piece, ensure_ascii=False)}\n\n"
                                        await _asyncio.sleep(CHUNK_DELAY)

                    # LLM token 流式输出 — 只放行白名单节点
                    if kind == "on_chat_model_stream" and event_node in STREAMING_NODES:
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            chunks_emitted = True
                            assistant_buffer.append(chunk.content)
                            yield f"data: {json.dumps(chunk.content, ensure_ascii=False)}\n\n"

                yield f"data: {json.dumps({'status': 'done'})}\n\n"

                # 持久化本轮对话到 messages 表
                full_answer = "".join(assistant_buffer)
                if full_answer:
                    try:
                        from app.services.memory_service import MemoryService
                        await MemoryService.save_message_pair(thread_id, query, full_answer)
                    except Exception:
                        logger.warning(f"save_message_pair failed for thread {thread_id}")

                # 后台记忆维护 — 必须在 astream_events 循环结束后调度,
                # 否则 summarize_if_needed 的 LLM token 流会被 astream_events 捕获,
                # 和 merge/respond 的 token 在 SSE 流上字符级交错 (跨流污染)。
                try:
                    import asyncio as _asyncio
                    from app.services.memory_service import MemoryService
                    from app.services.segment_manager import SegmentManager
                    from app.services.profile_builder import update_user_profile_from_thread
                    from app.services.llm_factory import LLMFactory

                    bg_llm = LLMFactory.create_llm("flash")
                    _asyncio.create_task(
                        MemoryService.summarize_if_needed(
                            thread_id, bg_llm, threshold=10, keep_recent=8
                        )
                    )

                    # graph 没挂 checkpointer (memory 自管),aget_state 不可用 —
                    # SegmentManager 是 MySQL 落库的幂等查询,直接拿当前活跃段
                    segment_id = await SegmentManager.get_or_open_segment(thread_id)
                    _asyncio.create_task(
                        update_user_profile_from_thread(
                            thread_id, int(user_id), segment_id or None
                        )
                    )
                except Exception:
                    logger.exception("Failed to schedule background memory tasks")

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
