import pytest
from httpx import AsyncClient


async def _create_job(client: AsyncClient, recruiter_headers: dict[str, str]) -> str:
    """辅助：创建一个 active 职位，返回 job_id"""
    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "测试岗位",
            "description": "测试描述",
            "work_type": "onsite",
        },
        headers=recruiter_headers,
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_apply_as_seeker(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """求职者投递申请成功"""
    job_id = await _create_job(client, auth_headers_recruiter)

    resp = await client.post(
        "/api/applications/",
        json={
            "job_id": job_id,
            "resume_text": "我是求职者，有3年Python经验",
            "cover_letter": "期待加入",
        },
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["status"] == "pending"
    assert data["resume_text"] == "我是求职者，有3年Python经验"


@pytest.mark.asyncio
async def test_apply_as_recruiter_forbidden(
    client: AsyncClient,
    auth_headers_recruiter: dict[str, str],
) -> None:
    """招聘者投递失败"""
    # 先创建一个岗位（需要用 recruiter 自己来创建）
    create_resp = await client.post(
        "/api/jobs/",
        json={"title": "For apply test", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "我不应该能投递"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_apply_closed_job(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """投递已关闭的职位"""
    job_id = await _create_job(client, auth_headers_recruiter)

    # 关闭职位
    await client.patch(
        f"/api/jobs/{job_id}/status",
        json={"status": "closed"},
        headers=auth_headers_recruiter,
    )

    resp = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "投递关闭的职位"},
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_apply_duplicate_job(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """重复投递同一职位"""
    job_id = await _create_job(client, auth_headers_recruiter)

    # 第一次投递
    resp1 = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "第一次投递"},
        headers=auth_headers_seeker,
    )
    assert resp1.status_code == 201

    # 第二次投递同一职位
    resp2 = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "第二次投递"},
        headers=auth_headers_seeker,
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_my_applications(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """查看自己的申请列表"""
    job_id = await _create_job(client, auth_headers_recruiter)

    await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "我的简历"},
        headers=auth_headers_seeker,
    )

    resp = await client.get(
        "/api/applications/my",
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_job_applications_as_owner(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """招聘者查看自己岗位的申请列表"""
    job_id = await _create_job(client, auth_headers_recruiter)

    await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "投递申请"},
        headers=auth_headers_seeker,
    )

    resp = await client.get(
        f"/api/applications/job/{job_id}",
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_job_applications_not_owner(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """非拥有者查看岗位申请列表失败"""
    job_id = await _create_job(client, auth_headers_recruiter)

    # 求职者尝试查看岗位的申请列表
    resp = await client.get(
        f"/api/applications/job/{job_id}",
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_application_status(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """招聘者更新申请状态"""
    job_id = await _create_job(client, auth_headers_recruiter)

    apply_resp = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "状态更新测试"},
        headers=auth_headers_seeker,
    )
    application_id = apply_resp.json()["id"]

    resp = await client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "interview"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "interview"


@pytest.mark.asyncio
async def test_apply_rejected_job_blocked(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """被拒绝后无法再次申请（force=false）"""
    job_id = await _create_job(client, auth_headers_recruiter)

    # 求职者投递
    apply_resp = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "我的简历"},
        headers=auth_headers_seeker,
    )
    assert apply_resp.status_code == 201
    application_id = apply_resp.json()["id"]

    # 招聘者拒绝
    reject_resp = await client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "rejected"},
        headers=auth_headers_recruiter,
    )
    assert reject_resp.status_code == 200

    # 再次申请同一职位（force=false，默认）
    resp = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "再次申请"},
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 403
    assert "该岗位已拒绝您的投递，无法再次申请" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_apply_rejected_job_force_blocked(
    client: AsyncClient,
    auth_headers_seeker: dict[str, str],
    auth_headers_recruiter: dict[str, str],
) -> None:
    """被拒绝后即使 force=true 也无法再次申请"""
    job_id = await _create_job(client, auth_headers_recruiter)

    # 求职者投递
    apply_resp = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "我的简历"},
        headers=auth_headers_seeker,
    )
    assert apply_resp.status_code == 201
    application_id = apply_resp.json()["id"]

    # 招聘者拒绝
    reject_resp = await client.patch(
        f"/api/applications/{application_id}/status",
        json={"status": "rejected"},
        headers=auth_headers_recruiter,
    )
    assert reject_resp.status_code == 200

    # 再次申请同一职位（force=true 仍然被拒）
    resp = await client.post(
        "/api/applications/?force=true",
        json={"job_id": job_id, "resume_text": "强制再次申请"},
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 403
    assert "该岗位已拒绝您的投递，无法再次申请" in resp.json()["detail"]
