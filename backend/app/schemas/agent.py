import uuid
from datetime import datetime
from typing import Optional, Any, Literal

from pydantic import BaseModel, Field, field_serializer

from app.models.evaluation_task import EvalTaskStatus


# ── LLM 输出结构化 Schema ──────────────────────────────────


class DimensionScore(BaseModel):
    """单个评估维度评分"""

    name: str = Field(..., description="维度名称")
    score: float = Field(..., ge=0, le=100, description="0-100 分")
    weight: float = Field(..., ge=0, le=1, description="权重 0-1")
    reason: str = Field(..., description="评估理由")


class ResumeEvaluation(BaseModel):
    """单份简历评估结果"""

    dimensions: list[DimensionScore] = Field(..., description="各维度评分")
    weighted_total: float = Field(..., ge=0, le=100, description="加权总分")
    suggestion: Literal["recommend", "reject", "neutral"] = Field(
        ..., description="AI 建议决策"
    )
    summary: str = Field(..., description="一句话总结")


class BorderlineReview(BaseModel):
    """边界候选人复评结果"""

    application_id: str = Field(..., description="申请 ID")
    action: Literal["keep", "adjust"] = Field(..., description="维持或调整")
    new_decision: Optional[Literal["recommend", "reject"]] = Field(
        None, description="调整后的决策（action=adjust 时必填）"
    )
    reason: str = Field(..., description="调整理由")


class IntentResult(BaseModel):
    """意图识别结果"""

    intent: Literal[
        "evaluate",
        "list_jobs",
        "job_detail",
        "pending_count",
        "interview_count",
        "candidate_eval",
        "funnel",
        "candidate_list",
        "status_change",
        "job_status",
        "confirm",
        "cancel",
        "help",
        "unknown",
    ] = Field(
        ..., description="识别出的意图类型"
    )
    confidence: float = Field(
        ..., ge=0, le=1, description="置信度 0-1"
    )
    extracted_params: dict[str, Any] = Field(
        default_factory=dict,
        description="提取的参数（各意图对应不同参数键）",
    )
    clarifying_question: str | None = Field(
        None, description="置信度低时的追问（仅 unknown 时）"
    )


# ── Agent API 请求/响应 Schema ──────────────────────────────


class EvaluateRequest(BaseModel):
    """触发评估请求"""

    interview_quota: Optional[int] = Field(
        None, description="面试人数上限，null 表示不限（可覆盖岗位设定）"
    )


class EvaluateResponse(BaseModel):
    """触发评估响应"""

    task_id: str
    status: str = "pending"
    total_count: int = 0

    @field_serializer("task_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""

    task_id: str
    job_id: str
    status: EvalTaskStatus
    total_count: int = 0
    evaluated_count: int = 0
    result_summary: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("task_id", "job_id")
    def serialize_uuid(self, value: uuid.UUID | str, _info: Any) -> str:
        return str(value)


class ConfirmDecision(BaseModel):
    """单个申请的确认决策"""

    application_id: str = Field(..., description="申请 ID")
    final_decision: Literal["interview", "reject"] = Field(
        ..., description="最终决策"
    )
    override_reason: Optional[str] = Field(
        None, description="覆盖 AI 决策时的理由"
    )


class ConfirmRequest(BaseModel):
    """确认评估结果请求"""

    decisions: list[ConfirmDecision] = Field(
        default_factory=list,
        description="逐个覆盖 AI 决策；为空则按 AI 建议批量更新",
    )


class ConfirmResponse(BaseModel):
    """确认评估结果响应"""

    updated_count: int
    message: str
