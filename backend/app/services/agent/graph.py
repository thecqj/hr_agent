"""LangGraph 评估工作流图定义"""

from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.graph import StateGraph, END

from app.services.agent.state import EvaluationState
from app.services.agent.nodes import (
    collect_node,
    evaluate_node,
    screen_node,
    review_node,
    save_draft_node,
)


def build_evaluation_graph() -> StateGraph:  # type: ignore[type-arg]
    """构建评估工作流图

    流程：collect → evaluate → screen → review → save_draft → END

    Note: add_node 的 type: ignore[call-overload] 是因为我们的节点函数
    签名 (EvaluationState, AsyncSession) 与 LangGraph 期望的
    (EvaluationState,) 不匹配。Phase 1 采用手动顺序调用方式，
    graph 定义仅供参考；Phase 2 会引入 checkpoint 后重构签名。
    """
    graph = StateGraph(EvaluationState)

    # 添加节点
    graph.add_node("collect", collect_node)  # type: ignore[call-overload]
    graph.add_node("evaluate", evaluate_node)  # type: ignore[call-overload]
    graph.add_node("screen", screen_node)  # type: ignore[call-overload]
    graph.add_node("review", review_node)  # type: ignore[call-overload]
    graph.add_node("save_draft", save_draft_node)  # type: ignore[call-overload]

    # 设置入口
    graph.set_entry_point("collect")

    # 定义边
    graph.add_edge("collect", "evaluate")
    graph.add_edge("evaluate", "screen")
    graph.add_edge("screen", "review")
    graph.add_edge("review", "save_draft")
    graph.add_edge("save_draft", END)

    return graph


async def run_evaluation_workflow(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """执行完整的评估工作流

    由于 LangGraph 的节点函数签名需要 db session，
    我们手动依次执行各节点（Phase 1 简化方案）。
    LangGraph checkpoint 等高级特性在 Phase 2 补充。
    """
    # collect
    state = await collect_node(state, db)

    # 如果 collect 阶段出现致命错误（没有申请），直接返回
    if not state.get("applications"):
        return state

    # evaluate
    state = await evaluate_node(state, db)

    # 如果所有评估都失败，直接返回
    if not state.get("evaluation_results"):
        return state

    # screen
    state = await screen_node(state, db)

    # review
    state = await review_node(state, db)

    # save_draft
    state = await save_draft_node(state, db)

    return state
