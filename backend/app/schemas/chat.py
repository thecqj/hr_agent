"""Chat API 请求/响应 Schema"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """发送聊天消息请求"""

    message: str = Field(
        ..., min_length=1, max_length=500, description="用户消息"
    )


# ── SSE 事件 Schema ─────────────────────────────────────────


class ThinkingEvent(BaseModel):
    """thinking 事件"""

    status: str


class IntentEvent(BaseModel):
    """intent 事件"""

    intent: str
    params: dict[str, Any] = Field(default_factory=dict)


class ProgressEvent(BaseModel):
    """progress 事件"""

    status: str
    evaluated_count: int | None = None
    total_count: int | None = None


class ErrorEvent(BaseModel):
    """error 事件"""

    message: str
    recoverable: bool


class EvaluationSummaryCard(BaseModel):
    """评估摘要卡片"""

    type: Literal["evaluation_summary"] = "evaluation_summary"
    task_id: str
    job_title: str
    total_count: int
    recommended_count: int
    rejected_count: int
    result_page_url: str


class ResultEvent(BaseModel):
    """result 事件"""

    reply_message: str
    cards: list[EvaluationSummaryCard] | None = None
