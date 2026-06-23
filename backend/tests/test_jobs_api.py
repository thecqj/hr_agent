import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_job_as_recruiter(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """招聘者创建职位成功"""
    resp = await client.post(
        "/api/v1/jobs/",
        json={
            "title": "Python 开发工程师",
            "description": "负责后端开发",
            "salary_min": 15,
            "salary_max": 30,
            "location": "北京",
            "work_type": "onsite",
            "skills_required": ["Python", "FastAPI"],
        },
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Python 开发工程师"
    assert data["status"] == "active"
    assert data["skills_required"] == ["Python", "FastAPI"]


@pytest.mark.asyncio
async def test_create_job_as_seeker_forbidden(
    client: AsyncClient, auth_headers_seeker: dict[str, str]
) -> None:
    """求职者创建职位失败"""
    resp = await client.post(
        "/api/v1/jobs/",
        json={
            "title": "不应该创建",
            "description": "测试",
            "work_type": "onsite",
        },
        headers=auth_headers_seeker,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_jobs_default_filter(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """列出职位 — 默认只返回 active"""
    # 创建一个 active 职位
    await client.post(
        "/api/v1/jobs/",
        json={"title": "Active Job", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    # 创建后关闭一个
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "To Close", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]
    await client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "closed"},
        headers=auth_headers_recruiter,
    )

    resp = await client.get("/api/v1/jobs/", headers=auth_headers_recruiter)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    # 默认只返回 active
    for item in data["items"]:
        assert item["status"] == "active"


@pytest.mark.asyncio
async def test_list_jobs_keyword_search(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """列出职位 — 关键词搜索"""
    await client.post(
        "/api/v1/jobs/",
        json={"title": "Go 开发", "description": "云原生开发", "work_type": "remote"},
        headers=auth_headers_recruiter,
    )
    await client.post(
        "/api/v1/jobs/",
        json={"title": "Java 开发", "description": "企业级应用", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )

    resp = await client.get(
        "/api/v1/jobs/", params={"keyword": "Go"}, headers=auth_headers_recruiter
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert "Go" in item["title"] or "Go" in item["description"]


@pytest.mark.asyncio
async def test_list_jobs_salary_filter(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """列出职位 — 薪资范围过滤"""
    await client.post(
        "/api/v1/jobs/",
        json={
            "title": "高薪岗位",
            "description": "desc",
            "salary_min": 30,
            "salary_max": 50,
            "work_type": "onsite",
        },
        headers=auth_headers_recruiter,
    )

    resp = await client.get(
        "/api/v1/jobs/",
        params={"salary_min": 25, "salary_max": 55},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        # 岗位 salary_max >= 过滤 salary_min 且 岗位 salary_min <= 过滤 salary_max
        if item["salary_min"] is not None and item["salary_max"] is not None:
            assert item["salary_max"] >= 25
            assert item["salary_min"] <= 55


@pytest.mark.asyncio
async def test_get_job_detail(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """获取单个职位"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "详情测试", "description": "详情desc", "work_type": "hybrid"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "详情测试"
    assert resp.json()["work_type"] == "hybrid"


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient) -> None:
    """获取不存在的职位"""
    resp = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_own_job(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """招聘者更新自己的职位"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "更新前", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/jobs/{job_id}",
        json={"title": "更新后"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "更新后"


@pytest.mark.asyncio
async def test_update_other_job_forbidden(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """更新他人职位失败"""
    # 先用 recruiter 创建一个职位
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "别人的", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    # 注册另一个招聘者尝试更新
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "other_recruiter@test.com",
            "password": "testpass123",
            "name": "其他招聘者",
            "role": "recruiter",
        },
    )
    other_token = reg_resp.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    resp = await client.put(
        f"/api/v1/jobs/{job_id}",
        json={"title": "篡改"},
        headers=other_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_own_job(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """删除自己的职位"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "待删除", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers_recruiter)
    assert resp.status_code == 200

    # 确认已删除
    get_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_job_forbidden(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """删除他人职位失败"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "不可删", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    # 注册另一个招聘者
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "deleter@test.com",
            "password": "testpass123",
            "name": "删除者",
            "role": "recruiter",
        },
    )
    other_headers = {"Authorization": f"Bearer {reg_resp.json()['access_token']}"}

    resp = await client.delete(f"/api/v1/jobs/{job_id}", headers=other_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_job_status(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """更新职位状态"""
    create_resp = await client.post(
        "/api/v1/jobs/",
        json={"title": "状态测试", "description": "desc", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/jobs/{job_id}/status",
        json={"status": "closed"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
