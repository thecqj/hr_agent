"""HR Agent ReAct 对话 — Agent 图定义

使用 create_react_agent 替代原有的 14 节点意图分类图。
LLM 自主推理并选择 Tool，实现多步查询和灵活回复。
"""

from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.services.conversation.tools import (
    query_jobs,
    query_applications,
    query_evaluation,
    trigger_evaluation,
    confirm_evaluation,
    update_candidate_status,
    update_job_status,
)
from app.services.conversation.prompts import build_state_modifier


# All 7 tools
ALL_TOOLS = [
    query_jobs,
    query_applications,
    query_evaluation,
    trigger_evaluation,
    confirm_evaluation,
    update_candidate_status,
    update_job_status,
]


def build_conversation_graph(
    checkpointer: AsyncPostgresSaver,
    *,
    context: dict[str, object] | None = None,
) -> CompiledStateGraph:  # type: ignore[type-arg]
    """构建 ReAct 对话 Agent 图。

    Args:
        checkpointer: LangGraph PostgreSQL 持久化存储
        context: 可选的上下文字典，注入到 system prompt
                 (session_summary)

    Returns:
        编译后的 ReAct agent 图
    """
    chat_model = ChatOpenAI(
        model=settings.CHAT_MODEL,
        api_key=SecretStr(settings.DEEPSEEK_API_KEY) if settings.DEEPSEEK_API_KEY else None,
        base_url=settings.DEEPSEEK_BASE_URL,
        temperature=0.3,
    )

    state_modifier = build_state_modifier(context or {})

    graph = create_react_agent(
        model=chat_model,
        tools=ALL_TOOLS,
        checkpointer=checkpointer,
        prompt=state_modifier,
    )

    return graph
