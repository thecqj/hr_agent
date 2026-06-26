"""LangGraph 评估工作流图定义 & 执行"""

from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.runnables import RunnableConfig

from app.services.agent.state import EvaluationState
from app.services.agent.nodes import (
    collect_node,
    evaluate_node,
    screen_node,
    review_node,
    save_draft_node,
)


def build_evaluation_graph(
    checkpointer: AsyncPostgresSaver,
) -> CompiledStateGraph:  # type: ignore[type-arg]
    """构建评估工作流图并编译

    流程：collect → evaluate → screen → review → save_draft → END

    Args:
        checkpointer: LangGraph PostgreSQL 持久化存储
    """
    graph = StateGraph(EvaluationState)

    # 添加节点
    graph.add_node("collect", collect_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("screen", screen_node)
    graph.add_node("review", review_node)
    graph.add_node("save_draft", save_draft_node)

    # 设置入口
    graph.set_entry_point("collect")

    # 定义边
    graph.add_edge("collect", "evaluate")
    graph.add_edge("evaluate", "screen")
    graph.add_edge("screen", "review")
    graph.add_edge("review", "save_draft")
    graph.add_edge("save_draft", END)

    return graph.compile(checkpointer=checkpointer)


async def run_evaluation_workflow(
    state: EvaluationState,
    db: AsyncSession,
) -> EvaluationState:
    """执行完整的评估工作流（通过 LangGraph 图引擎）

    使用 ainvoke 执行图，db session 通过 configurable 传入。
    对于需要 SSE 流式事件的场景，直接使用 build_evaluation_graph()
    配合 astream_events() 调用。
    """
    from app.database import get_checkpointer

    checkpointer = get_checkpointer()
    graph = build_evaluation_graph(checkpointer)

    config: RunnableConfig = {
        "configurable": {
            "thread_id": state.get("task_id", "default"),
            "db": db,
        }
    }

    result: dict[str, object] = await graph.ainvoke(state, config=config)

    # ainvoke 返回完整状态 dict，类型兼容 EvaluationState
    return result  # type: ignore[return-value]
