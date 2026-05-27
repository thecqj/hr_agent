from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.services.agent.state import AgentState
from app.services.agent.nodes import (
    agent_node,
    tool_execution_node,
    response_node,
    should_continue,
)

def build_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_execution_node)
    workflow.add_node("respond", response_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "respond": "respond",
            "__end__": END,
        }
    )
    workflow.add_edge("tools", "agent")
    workflow.add_edge("respond", END)
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

agent_graph = build_agent_graph()