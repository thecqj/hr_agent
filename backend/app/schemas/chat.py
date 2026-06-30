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


# ── 卡片 Schema ─────────────────────────────────────────────


class EvaluationSummaryCard(BaseModel):
    """评估摘要卡片"""

    type: Literal["evaluation_summary"] = "evaluation_summary"
    task_id: str
    job_title: str
    total_count: int
    recommended_count: int
    rejected_count: int
    result_page_url: str


class JobListCard(BaseModel):
    """岗位列表卡片"""

    type: Literal["job_list"] = "job_list"
    jobs: list[dict[str, Any]] = Field(
        ..., description="岗位列表，每项含 job_code/title/status/head_count"
    )


class JobDetailCard(BaseModel):
    """岗位详情卡片"""

    type: Literal["job_detail"] = "job_detail"
    job: dict[str, Any] = Field(
        ..., description="岗位完整信息"
    )


class FunnelStage(BaseModel):
    """漏斗阶段"""

    status: str = Field(..., description="阶段状态名称")
    count: int = Field(..., description="该阶段数量")
    percentage: float = Field(..., description="占总量百分比")


class FunnelCard(BaseModel):
    """招聘漏斗卡片"""

    type: Literal["funnel"] = "funnel"
    job_code: str = Field(..., description="岗位编号")
    job_title: str = Field(..., description="岗位名称")
    stages: list[FunnelStage] = Field(..., description="各阶段数据")


class CandidateItem(BaseModel):
    """候选人条目"""

    name: str = Field(..., description="候选人姓名")
    ai_score: float | None = Field(None, description="AI 评分")
    ai_decision: str | None = Field(None, description="AI 决策: recommend/reject")
    status: str = Field(..., description="当前状态")


class CandidateListCard(BaseModel):
    """候选人列表卡片"""

    type: Literal["candidate_list"] = "candidate_list"
    job_code: str = Field(..., description="岗位编号")
    job_title: str = Field(..., description="岗位名称")
    candidates: list[CandidateItem] = Field(..., description="候选人列表")


class ConfirmCard(BaseModel):
    """操作确认卡片"""

    type: Literal["confirm"] = "confirm"
    action: str = Field(..., description="操作描述")
    params: dict[str, Any] = Field(..., description="操作参数")


# 联合类型：所有卡片类型的 Union
ChatCard = (
    EvaluationSummaryCard
    | JobListCard
    | JobDetailCard
    | FunnelCard
    | CandidateListCard
    | ConfirmCard
)


class ResultEvent(BaseModel):
    """result 事件"""

    reply_message: str
    cards: list[ChatCard] | None = None
