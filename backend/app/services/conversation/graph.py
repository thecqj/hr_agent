"""对话 Agent LangGraph 图定义"""

from langgraph.graph import StateGraph, END, START
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.services.conversation.state import ConversationState
from app.services.conversation.nodes import (
    intent_node,
    dispatch_node,
    feedback_node,
    route_by_intent,
)


def build_conversation_graph(checkpointer: AsyncPostgresSaver) -> CompiledStateGraph:  # type: ignore[type-arg]
    """构建对话工作流图并编译

    流程：
    START → intent → (evaluate? → dispatch → feedback → END)
                   → (help/unknown? → feedback → END)
    """
    graph = StateGraph(ConversationState)

    # 添加节点
    graph.add_node("intent", intent_node)
    graph.add_node("dispatch", dispatch_node)
    graph.add_node("feedback", feedback_node)

    # 设置入口
    graph.add_edge(START, "intent")

    # 条件路由：intent → dispatch 或 feedback
    graph.add_conditional_edges(
        "intent",
        route_by_intent,
        {"dispatch": "dispatch", "feedback": "feedback"},
    )

    # dispatch → feedback → END
    graph.add_edge("dispatch", "feedback")
    graph.add_edge("feedback", END)

    return graph.compile(checkpointer=checkpointer)
