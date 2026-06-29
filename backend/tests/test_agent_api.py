"""Agent API 集成测试"""

from typing import Any

import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_trigger_evaluation_unauthorized(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """求职者不能触发评估"""
    # 用招聘者创建一个岗位
    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "测试岗位-权限",
            "description": "描述",
            "requirements": "3年以上开发经验",
            "skills_required": ["Python"],
        },
        headers=auth_headers_recruiter,
    )
    job_id = resp.json()["id"]

    # 求职者尝试触发评估
    resp = await client.post(
        f"/api/agent/evaluate/{job_id}",
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_trigger_evaluation_not_owner(
    client: AsyncClient,
    recruiter_with_job: dict[str, Any],
) -> None:
    """非岗位 owner 的招聘者不能触发评估"""
    job_id = recruiter_with_job["job_id"]

    # 创建另一个招聘者
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "other-recruiter@test.com",
            "password": "testpass123",
            "name": "其他招聘者",
            "role": "recruiter",
        },
    )
    other_headers: dict[str, str] = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await client.post(
        f"/api/agent/evaluate/{job_id}",
        headers=other_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_trigger_evaluation_job_not_found(
    client: AsyncClient,
    auth_headers_recruiter: dict[str, str],
) -> None:
    """评估不存在的岗位返回 404"""
    resp = await client.post(
        "/api/agent/evaluate/00000000-0000-0000-0000-000000000000",
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_task_status_not_found(
    client: AsyncClient,
    auth_headers_recruiter: dict[str, str],
) -> None:
    """查询不存在的任务返回 404"""
    resp = await client.get(
        "/api/agent/task/00000000-0000-0000-0000-000000000000",
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_confirm_task_not_found(
    client: AsyncClient,
    recruiter_with_job: dict[str, Any],
) -> None:
    """确认不存在的任务返回 404"""
    recruiter_headers: dict[str, str] = recruiter_with_job["recruiter_headers"]
    resp = await client.post(
        "/api/agent/confirm/00000000-0000-0000-0000-000000000000",
        headers=recruiter_headers,
    )
    # 任务不存在 → 404
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_trigger_evaluation_success(
    client: AsyncClient,
    recruiter_with_job: dict[str, Any],
) -> None:
    """成功触发评估"""
    job_id = recruiter_with_job["job_id"]
    recruiter_headers: dict[str, str] = recruiter_with_job["recruiter_headers"]

    # Mock 后台工作流，避免真实 LLM 调用
    with patch(
        "app.services.agent_service._run_workflow_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            headers=recruiter_headers,
        )

    assert resp.status_code == 201
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    assert data["total_count"] == 3


@pytest.mark.asyncio
async def test_trigger_duplicate_evaluation(
    client: AsyncClient,
    recruiter_with_job: dict[str, Any],
) -> None:
    """重复触发评估返回 409"""
    job_id = recruiter_with_job["job_id"]
    recruiter_headers: dict[str, str] = recruiter_with_job["recruiter_headers"]

    with patch(
        "app.services.agent_service._run_workflow_background",
        new_callable=AsyncMock,
    ):
        # 第一次触发
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            headers=recruiter_headers,
        )
        assert resp.status_code == 201

        # 第二次触发
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            headers=recruiter_headers,
        )
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_task_status_after_trigger(
    client: AsyncClient,
    recruiter_with_job: dict[str, Any],
) -> None:
    """触发后查询任务状态"""
    job_id = recruiter_with_job["job_id"]
    recruiter_headers: dict[str, str] = recruiter_with_job["recruiter_headers"]

    with patch(
        "app.services.agent_service._run_workflow_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            headers=recruiter_headers,
        )
        task_id = resp.json()["task_id"]

    # 查询状态
    resp = await client.get(
        f"/api/agent/task/{task_id}",
        headers=recruiter_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == task_id
    assert data["status"] in ["pending", "running", "completed", "failed"]
    assert data["total_count"] == 3


@pytest.mark.asyncio
async def test_trigger_with_custom_quota(
    client: AsyncClient,
    recruiter_with_job: dict[str, Any],
) -> None:
    """触发评估时自定义面试人数上限"""
    job_id = recruiter_with_job["job_id"]
    recruiter_headers: dict[str, str] = recruiter_with_job["recruiter_headers"]

    with patch(
        "app.services.agent_service._run_workflow_background",
        new_callable=AsyncMock,
    ):
        resp = await client.post(
            f"/api/agent/evaluate/{job_id}",
            json={"interview_quota": 5},
            headers=recruiter_headers,
        )

    assert resp.status_code == 201
