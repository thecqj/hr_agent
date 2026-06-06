from typing import Any, Optional, TypedDict


class AgentState(TypedDict):
    """单智能体对话状态（占位）"""

    messages: list[dict[str, Any]]
    user_role: str
    user_id: str
    current_page: str
    context: dict[str, Any]
    user_profile: Optional[dict[str, Any]]
    next_action: str
    pending_tool_calls: list[dict[str, Any]]
    iteration_count: int
    final_response: Optional[str]


class MultiAgentState(TypedDict):
    """多智能体协同状态（占位）"""

    messages: list[dict[str, Any]]
    user_id: str
    job_id: str
    candidates: list[dict[str, Any]]
    structured_candidates: list[dict[str, Any]]
    scores: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    hr_decision: Optional[str]
    next_action: str
    iteration_count: int
    error: Optional[str]
