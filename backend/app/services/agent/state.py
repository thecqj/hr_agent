from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """单智能体对话状态"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_role: str
    user_id: str
    current_page: str
    context: Dict[str, Any]
    user_profile: Optional[Dict[str, Any]]
    next_action: Literal["continue", "respond", "end"]
    pending_tool_calls: List[Dict[str, Any]]
    iteration_count: int
    final_response: Optional[str]


class MultiAgentState(TypedDict):
    """多智能体协同状态"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    job_id: str                     # 目标岗位ID
    candidates: List[Dict[str, Any]] # 原始投递数据
    structured_candidates: List[Dict[str, Any]] # 结构化后的简历
    scores: List[Dict[str, float]]   # 匹配评分
    recommendations: List[Dict]      # 推荐结果（含理由）
    hr_decision: Optional[str]       # HR确认结果
    next_action: str                 # supervisor的调度指令
    iteration_count: int
    error: Optional[str]