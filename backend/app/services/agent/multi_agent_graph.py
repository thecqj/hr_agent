from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.services.agent.state import MultiAgentState
from app.services.agent.nodes import (
    supervisor_node,
    resume_parser_node,
    match_scoring_node,
    ranking_node,
    hr_review_node,
    notification_node,
    evaluate_node,
)

def build_multi_agent_graph():
    workflow = StateGraph(MultiAgentState)

    # 添加节点
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("resume_parser", resume_parser_node)
    workflow.add_node("match_scoring", match_scoring_node)
    workflow.add_node("ranking", ranking_node)
    workflow.add_node("hr_review", hr_review_node)
    workflow.add_node("notification", notification_node)
    workflow.add_node("evaluate", evaluate_node)

    # 入口
    workflow.set_entry_point("supervisor")

    # 从 supervisor 出发的条件边
    def route_from_supervisor(state):
        return state["next_action"]

    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "parse": "resume_parser",
            "score": "match_scoring",
            "rank": "ranking",
            "ask_hr": "hr_review",
            "notify": "notification",
            "evaluate": "evaluate",
            "end": END,
        }
    )

    # 子节点完成后回到 supervisor
    workflow.add_edge("resume_parser", "supervisor")
    workflow.add_edge("match_scoring", "supervisor")
    workflow.add_edge("ranking", "supervisor")
    workflow.add_edge("hr_review", "supervisor")
    workflow.add_edge("evaluate", END)  # 评估完成后直接结束
    workflow.add_edge("notification", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory, interrupt_before=["hr_review"])

multi_agent_graph = build_multi_agent_graph()