# lg_builder.py
# 职责：构建 LangGraph 状态机（整个 Agent 的"大脑"）
#
# 整体流程：
#   用户消息
#       ↓
#   analyze_and_route_query（判断问题类型）
#       ↓ 条件路由
#   ┌── general-query    → respond_to_general_query（直接回答）
#   ├── additional-query → get_additional_info（Guardrails 过滤 + 要求补充信息）
#   ├── graphrag-query   → create_research_plan（知识图谱检索 + 多工具子图）
#   └── image-query      → create_image_query（视觉模型分析图片）

from app.lg_agent.lg_states import AgentState, Router, InputState
from app.lg_agent.lg_prompts import (
    ROUTER_SYSTEM_PROMPT,
    GET_ADDITIONAL_SYSTEM_PROMPT,
    GENERAL_QUERY_SYSTEM_PROMPT,
    GUARDRAILS_SYSTEM_PROMPT,
)
from langchain_core.runnables import RunnableConfig
from app.core.config import settings
from app.services.llm_factory import LLMFactory
from app.core.logger import get_logger
from typing import cast, Literal, List, Dict, Any
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from app.lg_agent.kg_sub_graph.agentic_rag_agents.workflows.multi_agent.multi_tool import create_multi_tool_workflow
from app.lg_agent.kg_sub_graph.tools import predefined_cypher, cypher_query
from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.cypher_dict import predefined_cypher_dict
from app.lg_agent.kg_sub_graph.neo4j_conn import get_neo4j_graph
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
import base64
import aiohttp
from pathlib import Path


logger = get_logger(service="lg_builder")


def _get_model(temperature: float = 0.7, tags: list = None):
    return LLMFactory.create_agent_llm(temperature=temperature)


# ── 节点1：路由判断 ────────────────────────────────────────────────────────────

async def analyze_and_route_query(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, Router]:
    model = _get_model()

    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT}
    ] + state.messages
    logger.info("-----Analyze user query type-----")

    response = cast(
        Router, await model.with_structured_output(Router).ainvoke(messages)
    )
    logger.info(f"Router type: {response['type']}, logic: {response['logic']}")
    return {"router": response}


# ── 条件路由函数 ───────────────────────────────────────────────────────────────

def route_query(
    state: AgentState,
) -> Literal["respond_to_general_query", "get_additional_info", "create_research_plan", "create_image_query"]:
    _type = state.router["type"]

    if _type == "general-query":
        return "respond_to_general_query"
    elif _type == "additional-query":
        return "get_additional_info"
    elif _type == "graphrag-query":
        return "create_research_plan"
    elif _type == "image-query":
        return "create_image_query"
    else:
        raise ValueError(f"Unknown router type {_type}")


# ── 节点2：普通问题直接回答 ────────────────────────────────────────────────────

async def respond_to_general_query(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    logger.info("-----generate general-query response-----")
    model = _get_model()
    messages = [{"role": "system", "content": GENERAL_QUERY_SYSTEM_PROMPT}] + state.messages
    response = await model.ainvoke(messages)
    return {"messages": [response]}


# ── 守卫：拦截超出经营范围的询问 ─────────────────────────────────────────────

class AdditionalGuardrailsOutput(BaseModel):
    decision: Literal["end", "continue"] = Field(
        description="Decision on whether the question is related to the graph contents."
    )


# ── 节点3：守卫过滤 + 补充信息 ────────────────────────────────────────────────

async def get_additional_info(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    """先守卫拦截，再引导补充信息"""
    logger.info("------continue to get additional info------")
    model = _get_model()
    neo4j_graph = get_neo4j_graph()

    scope_description = """
    电商经营范围：智能家居与消费电子产品，包括但不限于：
    - 智能空调、智能冰箱、智能洗衣机、智能电视
    - 智能门锁、智能门铃、智能摄像头、智能窗帘
    - 智能音箱、智能手环、智能体重秤、智能马桶
    - 智能空气净化器、智能净水器、智能加湿器
    - 智能电饭煲、智能灯具、智能扫地机器人

    不包含：服装、鞋类、体育用品、化妆品、食品等非电子产品。
    """

    labels = [r['label'] for r in neo4j_graph.query("CALL db.labels()")]
    graph_context = f"\n数据库包含以下类型: {', '.join(labels)}"
    message = f"参考此范围描述来决策:\n{scope_description}{graph_context}\nQuestion: {{question}}"

    guardrails_prompt = ChatPromptTemplate.from_messages([
        ("system", GUARDRAILS_SYSTEM_PROMPT),
        ("human", message),
    ])
    # 拼接最近 3 轮对话作为上下文，避免"50"被误判
    def _msg_text(m):
        if isinstance(m, dict): return m.get("content", "")
        return getattr(m, "content", "") or ""
    question = _msg_text(state.messages[-1])
    recent = state.messages[:-1][-4:] if len(state.messages) > 1 else []
    history = "\n".join(f"用户: {_msg_text(m)}" for m in recent)
    guardrails_question = f"{history}\n用户: {question}" if history else question

    guardrails_chain = guardrails_prompt | model.with_structured_output(AdditionalGuardrailsOutput)
    guardrails_output = await guardrails_chain.ainvoke({"question": guardrails_question})

    if guardrails_output.decision == "end":
        return {"messages": [AIMessage(content="很抱歉，您的问题超出了我们的服务范围。我们专注于智能家居产品的咨询服务，如有相关问题欢迎继续提问。")]}

    additional_info_prompt = ChatPromptTemplate.from_messages([
        ("system", GET_ADDITIONAL_SYSTEM_PROMPT),
        ("human", "{question}"),
    ])
    additional_info_chain = additional_info_prompt | model
    response = await additional_info_chain.ainvoke({"question": guardrails_question})
    return {"messages": [response]}


# ── 节点4：图片分析 ────────────────────────────────────────────────────────────

async def create_image_query(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    logger.info("-----Found User Upload Image-----")
    image_path = config.get("configurable", {}).get("image_path", None)

    if not image_path or not Path(image_path).exists():
        logger.warning(f"User Upload Image Not Found: {image_path}")
        return {"messages": [AIMessage(content="抱歉，我无法查看这张图片，请重新上传。")]}

    api_key = settings.VISION_API_KEY
    vision_model = settings.VISION_MODEL

    if not api_key or not vision_model:
        logger.error("Vision Model Configuration Not Complete")
        return {"messages": [AIMessage(content="抱歉，图片分析功能未配置。")]}

    logger.info(f"Using Vision Model: {vision_model}")

    try:
        from PIL import Image
        import io

        with Image.open(image_path) as img:
            max_size = 1024
            width, height = img.size
            ratio = min(max_size / width, max_size / height)

            if width <= max_size and height <= max_size:
                resized_img = img
            else:
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)

            img_byte_arr = io.BytesIO()
            if resized_img.mode in ('RGBA', 'LA'):
                resized_img = resized_img.convert('RGB')
            resized_img.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr = img_byte_arr.getvalue()

        base64_image = base64.b64encode(img_byte_arr).decode('utf-8')
        mime_type = "image/jpeg"

        dashscope_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        request_body = {
            "model": vision_model,
            "input": {
                "messages": [{
                    "role": "user",
                    "content": [
                        {"image": f"data:{mime_type};base64,{base64_image}"},
                        {"text": state.messages[-1].content if state.messages else "请描述这张图片"}
                    ]
                }]
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                dashscope_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=request_body
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    output = result.get("output", {})
                    choices = output.get("choices", [])
                    if choices:
                        content_list = choices[0].get("message", {}).get("content", [])
                        text_parts = [c.get("text", "") for c in content_list if c.get("text")]
                        content = "".join(text_parts)
                        return {"messages": [AIMessage(content=content)]}
                    return {"messages": [AIMessage(content="抱歉，图片分析未能返回结果。")]}
                else:
                    error_text = await response.text()
                    logger.error(f"Vision API Error: {response.status}, {error_text}")
                    return {"messages": [AIMessage(content="抱歉，图片分析失败，请重试。")]}

    except Exception as e:
        logger.error(f"Image processing error: {str(e)}")
        return {"messages": [AIMessage(content=f"抱歉，处理图片时出错：{str(e)}")]}


# ── 节点5：知识库查询（最复杂的节点）─────────────────────────────────────────

async def create_research_plan(
    state: AgentState, *, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    logger.info("------execute local knowledge base query------")

    model = _get_model()
    neo4j_graph = get_neo4j_graph()

    tool_schemas: List[type[BaseModel]] = [predefined_cypher, cypher_query]

    multi_tool_workflow = create_multi_tool_workflow(
        llm=model,
        graph=neo4j_graph,
        tool_schemas=tool_schemas,
        predefined_cypher_dict=predefined_cypher_dict,
    )

    input_state = {
        "messages": state.messages,
        "question": state.messages[-1]["content"] if isinstance(state.messages[-1], dict) else state.messages[-1].content,
        "steps": [],
    }

    response = await multi_tool_workflow.ainvoke(input_state)
    answer = response.get("answer", "")
    return {"messages": [AIMessage(content=answer)]}


# ── 构建状态机图 ───────────────────────────────────────────────────────────────

checkpointer = MemorySaver()

builder = StateGraph(AgentState, input=InputState)

builder.add_node(analyze_and_route_query)
builder.add_node(respond_to_general_query)
builder.add_node(get_additional_info)
builder.add_node("create_research_plan", create_research_plan)
builder.add_node(create_image_query)

builder.add_edge(START, "analyze_and_route_query")
builder.add_conditional_edges("analyze_and_route_query", route_query)

graph = builder.compile(checkpointer=checkpointer)
