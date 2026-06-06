from typing import Any


async def agent_node(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [],
        "next_action": "respond",
        "final_response": "AI 功能暂未启用，当前返回占位结果。",
    }


async def tool_execution_node(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [],
        "next_action": "continue",
        "pending_tool_calls": [],
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def response_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"next_action": "end"}


def should_continue(state: dict[str, Any]) -> str:
    if state.get("next_action") == "continue":
        return "tools"
    if state.get("next_action") == "respond":
        return "respond"
    return "__end__"


async def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"next_action": "end"}


async def resume_parser_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"structured_candidates": []}


async def match_scoring_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"scores": []}


async def ranking_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"recommendations": [], "next_action": "end"}


async def hr_review_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"next_action": "end"}


async def notification_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"next_action": "end"}


async def evaluate_node(state: dict[str, Any]) -> dict[str, Any]:
    return {"scores": [], "next_action": "end"}
