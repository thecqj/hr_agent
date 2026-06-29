import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_job_as_recruiter(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """招聘者创建职位成功"""
    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "Python 开发工程师",
            "description": "负责后端开发",
            "requirements": "3年以上Python开发经验",
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
    assert data["job_code"].startswith("J")
    assert len(data["job_code"]) == 6
    assert data["interview_quota"] == 1  # default
    assert data["head_count"] == 1       # default


@pytest.mark.asyncio
async def test_create_job_as_seeker_forbidden(
    client: AsyncClient, auth_headers_seeker: dict[str, str]
) -> None:
    """求职者创建职位失败"""
    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "不应该创建",
            "description": "测试",
            "requirements": "测试",
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
        "/api/jobs/",
        json={"title": "Active Job", "description": "desc", "requirements": "无", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    # 创建后关闭一个
    create_resp = await client.post(
        "/api/jobs/",
        json={"title": "To Close", "description": "desc", "requirements": "无", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]
    await client.patch(
        f"/api/jobs/{job_id}/status",
        json={"status": "closed"},
        headers=auth_headers_recruiter,
    )

    resp = await client.get("/api/jobs/", headers=auth_headers_recruiter)
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
        "/api/jobs/",
        json={"title": "Go 开发", "description": "云原生开发", "requirements": "Go语言经验", "work_type": "remote"},
        headers=auth_headers_recruiter,
    )
    await client.post(
        "/api/jobs/",
        json={"title": "Java 开发", "description": "企业级应用", "requirements": "Java经验", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )

    resp = await client.get(
        "/api/jobs/", params={"keyword": "Go"}, headers=auth_headers_recruiter
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
        "/api/jobs/",
        json={
            "title": "高薪岗位",
            "description": "desc",
            "requirements": "无",
            "salary_min": 30,
            "salary_max": 50,
            "work_type": "onsite",
        },
        headers=auth_headers_recruiter,
    )

    resp = await client.get(
        "/api/jobs/",
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
        "/api/jobs/",
        json={"title": "详情测试", "description": "详情desc", "requirements": "无", "work_type": "hybrid"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/api/jobs/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "详情测试"
    assert resp.json()["work_type"] == "hybrid"


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient) -> None:
    """获取不存在的职位"""
    resp = await client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_own_job(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """招聘者更新自己的职位"""
    create_resp = await client.post(
        "/api/jobs/",
        json={"title": "更新前", "description": "desc", "requirements": "无", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/jobs/{job_id}",
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
        "/api/jobs/",
        json={"title": "别人的", "description": "desc", "requirements": "无", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    # 注册另一个招聘者尝试更新
    reg_resp = await client.post(
        "/api/auth/register",
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
        f"/api/jobs/{job_id}",
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
        "/api/jobs/",
        json={"title": "待删除", "description": "desc", "requirements": "无", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/jobs/{job_id}", headers=auth_headers_recruiter)
    assert resp.status_code == 200

    # 确认已删除
    get_resp = await client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_job_forbidden(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """删除他人职位失败"""
    create_resp = await client.post(
        "/api/jobs/",
        json={"title": "不可删", "description": "desc", "requirements": "无", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    # 注册另一个招聘者
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "deleter@test.com",
            "password": "testpass123",
            "name": "删除者",
            "role": "recruiter",
        },
    )
    other_headers = {"Authorization": f"Bearer {reg_resp.json()['access_token']}"}

    resp = await client.delete(f"/api/jobs/{job_id}", headers=other_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_job_status(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """更新职位状态"""
    create_resp = await client.post(
        "/api/jobs/",
        json={"title": "状态测试", "description": "desc", "requirements": "无", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    job_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/jobs/{job_id}/status",
        json={"status": "closed"},
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_applications_count_reflects_real_count(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """岗位的 applications_count 应反映实际投递数"""
    # 1. 招聘者创建岗位
    create_resp = await client.post(
        "/api/jobs/",
        json={"title": "计数测试", "description": "desc", "requirements": "无", "work_type": "onsite"},
        headers=auth_headers_recruiter,
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]
    # 新建岗位 applications_count 应为 0
    assert create_resp.json()["applications_count"] == 0

    # 2. 注册求职者并投递
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "count_seeker@test.com",
            "password": "testpass123",
            "name": "计数求职者",
            "role": "job_seeker",
        },
    )
    seeker_token = reg_resp.json()["access_token"]
    seeker_headers = {"Authorization": f"Bearer {seeker_token}"}

    apply_resp = await client.post(
        "/api/applications/",
        json={"job_id": job_id, "resume_text": "测试简历"},
        headers=seeker_headers,
    )
    assert apply_resp.status_code == 201

    # 3. 招聘者再次查询岗位列表，applications_count 应为 1
    list_resp = await client.get(
        "/api/jobs/",
        params={"status": "all"},
        headers=auth_headers_recruiter,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    target = next((j for j in items if j["id"] == job_id), None)
    assert target is not None
    assert target["applications_count"] == 1

    # 4. 查询岗位详情，applications_count 也应为 1
    detail_resp = await client.get(f"/api/jobs/{job_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["applications_count"] == 1


@pytest.mark.asyncio
async def test_job_code_is_unique_and_auto_generated(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """Two jobs should get different job_codes"""
    resp1 = await client.post(
        "/api/jobs/",
        json={
            "title": "岗位A",
            "description": "描述A，至少十个字",
            "requirements": "无",
            "skills_required": [],
        },
        headers=auth_headers_recruiter,
    )
    resp2 = await client.post(
        "/api/jobs/",
        json={
            "title": "岗位B",
            "description": "描述B，至少十个字",
            "requirements": "无",
            "skills_required": [],
        },
        headers=auth_headers_recruiter,
    )
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    code1 = resp1.json()["job_code"]
    code2 = resp2.json()["job_code"]
    assert code1 != code2
    assert code1.startswith("J") and len(code1) == 6
    assert code2.startswith("J") and len(code2) == 6


@pytest.mark.asyncio
async def test_create_job_with_custom_quota_and_headcount(
    client: AsyncClient, auth_headers_recruiter: dict[str, str]
) -> None:
    """Creating a job with explicit interview_quota and head_count"""
    resp = await client.post(
        "/api/jobs/",
        json={
            "title": "岗位C",
            "description": "描述C，至少十个字",
            "requirements": "无",
            "interview_quota": 5,
            "head_count": 3,
        },
        headers=auth_headers_recruiter,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["interview_quota"] == 5
    assert data["head_count"] == 3
