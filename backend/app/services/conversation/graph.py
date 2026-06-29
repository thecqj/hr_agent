"""对话 Agent LangGraph 图定义"""

from typing import Any, Hashable

from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.services.conversation.state import ConversationState
from app.services.conversation.nodes import (
    intent_node,
    dispatch_node,
    feedback_node,
    route_by_intent,
    route_by_pending_action,
    list_jobs_node,
    job_detail_node,
    pending_count_node,
    interview_count_node,
    candidate_eval_node,
    funnel_node,
    candidate_list_node,
    confirm_node,
    cancel_node,
    status_change_node,
    job_status_action_node,
)


async def _noop_passthrough(state: ConversationState) -> dict[str, Any]:
    """空透传节点：用于 execute_action 路由中间层，不修改状态"""
    return {}


def build_conversation_graph(checkpointer: AsyncPostgresSaver) -> CompiledStateGraph:  # type: ignore[type-arg]
    """构建对话工作流图并编译

    流程：
    START → intent → route_by_intent →
      evaluate?       → dispatch → feedback → END
      <query_intent>? → <query_node> → feedback → END
      status_change / job_status? → confirm → feedback → END
      confirm? → execute_action → route_by_pending_action →
        status_change? → status_change → feedback → END
        job_status?    → job_status_action → feedback → END
      cancel? → cancel → feedback → END
      help/unknown? → feedback → END
    """
    graph = StateGraph(ConversationState)

    # ── 添加节点 ──────────────────────────────────────────────────
    graph.add_node("intent", intent_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("feedback", feedback_node)

    # 查询类节点
    graph.add_node("list_jobs", list_jobs_node)
    graph.add_node("job_detail", job_detail_node)
    graph.add_node("pending_count", pending_count_node)
    graph.add_node("interview_count", interview_count_node)
    graph.add_node("candidate_eval", candidate_eval_node)
    graph.add_node("funnel", funnel_node)
    graph.add_node("candidate_list", candidate_list_node)

    # 操作确认类节点
    graph.add_node("confirm", confirm_node)
    graph.add_node("cancel", cancel_node)
    graph.add_node("execute_action", _noop_passthrough)

    # 执行类节点
    graph.add_node("status_change", status_change_node)
    graph.add_node("job_status_action", job_status_action_node)

    # ── 设置入口 ──────────────────────────────────────────────────
    graph.add_edge(START, "intent")

    # ── 条件路由：intent → 各节点 ────────────────────────────────
    intent_routes: dict[Hashable, str] = {
        "dispatch": "dispatch",
        "feedback": "feedback",
        # 查询类
        "list_jobs": "list_jobs",
        "job_detail": "job_detail",
        "pending_count": "pending_count",
        "interview_count": "interview_count",
        "candidate_eval": "candidate_eval",
        "funnel": "funnel",
        "candidate_list": "candidate_list",
        # 操作确认
        "confirm": "confirm",
        "cancel": "cancel",
        # 执行操作（confirm → execute_action）
        "execute_action": "execute_action",
    }

    graph.add_conditional_edges("intent", route_by_intent, intent_routes)

    # ── 查询类节点 → feedback ────────────────────────────────────
    for node_name in (
        "list_jobs", "job_detail", "pending_count", "interview_count",
        "candidate_eval", "funnel", "candidate_list",
    ):
        graph.add_edge(node_name, "feedback")

    # dispatch → feedback
    graph.add_edge("dispatch", "feedback")

    # confirm → feedback
    graph.add_edge("confirm", "feedback")

    # cancel → feedback
    graph.add_edge("cancel", "feedback")

    # ── execute_action → 条件路由到具体执行节点 ───────────────────
    action_routes: dict[Hashable, str] = {
        "status_change": "status_change",
        "job_status_action": "job_status_action",
        "feedback": "feedback",
    }

    graph.add_conditional_edges("execute_action", route_by_pending_action, action_routes)

    # 执行类节点 → feedback
    graph.add_edge("status_change", "feedback")
    graph.add_edge("job_status_action", "feedback")

    # feedback → END
    graph.add_edge("feedback", END)

    return graph.compile(checkpointer=checkpointer)
