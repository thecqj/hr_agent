"""AgentService 单元测试"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.models.application import ApplicationStatus
from app.models.evaluation_task import EvalTaskStatus
from app.models.job import JobStatus
from app.models.user import UserRole
from app.schemas.agent import ConfirmRequest, ConfirmDecision
from app.services import agent_service


# ── trigger_evaluation 测试 ──────────────────────────────────


@pytest.mark.asyncio
async def test_trigger_non_recruiter_rejected() -> None:
    """非招聘者触发评估返回 403"""
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.role = UserRole.JOB_SEEKER

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.trigger_evaluation(
            mock_db, "job-1", mock_user, MagicMock()
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_trigger_job_not_found() -> None:
    """岗位不存在返回 404"""
    mock_db = AsyncMock()
    mock_db.get.return_value = None
    mock_user = MagicMock()
    mock_user.role = UserRole.RECRUITER

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.trigger_evaluation(
            mock_db, "nonexistent", mock_user, MagicMock()
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_trigger_not_job_owner() -> None:
    """非岗位 owner 触发返回 403"""
    mock_db = AsyncMock()
    mock_job = MagicMock()
    mock_job.recruiter_id = uuid.uuid4()  # 不同的 recruiter
    mock_db.get.return_value = mock_job
    mock_user = MagicMock()
    mock_user.role = UserRole.RECRUITER
    mock_user.id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.trigger_evaluation(
            mock_db, "job-1", mock_user, MagicMock()
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_trigger_duplicate_evaluation_returns_409() -> None:
    """重复触发评估返回 409"""
    job_uuid = uuid.uuid4()

    mock_db = AsyncMock()
    mock_job = MagicMock()
    mock_job.status = JobStatus.ACTIVE

    other_user_id = uuid.uuid4()
    mock_job.recruiter_id = other_user_id

    mock_user = MagicMock()
    mock_user.role = UserRole.RECRUITER
    mock_user.id = other_user_id

    # 模拟已存在 pending 任务
    mock_existing = MagicMock()
    mock_db.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=mock_existing)
    )
    mock_db.get.return_value = mock_job

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.trigger_evaluation(
            mock_db, str(job_uuid), mock_user, MagicMock()
        )
    assert exc_info.value.status_code == 409


# ── get_task_status 测试 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_task_not_found() -> None:
    """查询不存在的任务返回 404"""
    mock_db = AsyncMock()
    mock_db.get.return_value = None
    mock_user = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.get_task_status(mock_db, "nonexistent", mock_user)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_task_wrong_user() -> None:
    """非触发者查询任务返回 403"""
    mock_task = MagicMock()
    mock_task.triggered_by = uuid.uuid4()
    mock_db = AsyncMock()
    mock_db.get.return_value = mock_task

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()  # 不同的用户

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.get_task_status(mock_db, "task-1", mock_user)
    assert exc_info.value.status_code == 403


# ── confirm_evaluation 测试 ──────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_task_not_completed() -> None:
    """确认未完成的任务返回 400"""
    mock_task = MagicMock()
    mock_task.status = EvalTaskStatus.RUNNING
    mock_task.triggered_by = uuid.uuid4()
    mock_db = AsyncMock()
    mock_db.get.return_value = mock_task

    mock_user = MagicMock()
    mock_user.id = mock_task.triggered_by

    with pytest.raises(HTTPException) as exc_info:
        await agent_service.confirm_evaluation(
            mock_db, "task-1", mock_user, ConfirmRequest()
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_confirm_with_override_decisions() -> None:
    """确认时覆盖部分 AI 决策"""
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_task = MagicMock()
    mock_task.status = EvalTaskStatus.COMPLETED
    mock_task.triggered_by = user_id
    mock_task.job_id = job_id

    app1_id = uuid.uuid4()
    app2_id = uuid.uuid4()
    mock_app1 = MagicMock()
    mock_app1.id = app1_id
    mock_app1.ai_decision = "recommend"
    mock_app2 = MagicMock()
    mock_app2.id = app2_id
    mock_app2.ai_decision = "reject"

    mock_db = AsyncMock()
    # First get returns the task, second call never happens
    mock_db.get.return_value = mock_task
    mock_db.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_app1, mock_app2])))
    )

    mock_user = MagicMock()
    mock_user.id = user_id

    # 覆盖 app2 的决策为 interview
    request = ConfirmRequest(
        decisions=[
            ConfirmDecision(application_id=str(app2_id), final_decision="interview", override_reason="项目经验突出")
        ]
    )

    result = await agent_service.confirm_evaluation(mock_db, "task-1", mock_user, request)

    assert result.updated_count == 2
    # app1 用 AI 建议的 recommend → interview
    assert mock_app1.status == ApplicationStatus.INTERVIEW
    # app2 被覆盖为 interview
    assert mock_app2.status == ApplicationStatus.INTERVIEW
    # 任务状态更新为 confirmed
    assert mock_task.status == EvalTaskStatus.CONFIRMED
