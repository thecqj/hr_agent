import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_seeker(client: AsyncClient) -> None:
    """注册求职者成功"""
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "seeker_new@test.com",
            "password": "testpass123",
            "name": "新求职者",
            "role": "job_seeker",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "job_seeker"
    assert data["user"]["email"] == "seeker_new@test.com"


@pytest.mark.asyncio
async def test_register_recruiter(client: AsyncClient) -> None:
    """注册招聘者成功"""
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "recruiter_new@test.com",
            "password": "testpass123",
            "name": "新招聘者",
            "role": "recruiter",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["role"] == "recruiter"
    assert data["user"]["email"] == "recruiter_new@test.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    """重复邮箱注册失败"""
    payload = {
        "email": "dup@test.com",
        "password": "testpass123",
        "name": "重复用户",
        "role": "job_seeker",
    }
    resp1 = await client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """登录成功"""
    # 先注册
    await client.post(
        "/api/auth/register",
        json={
            "email": "login@test.com",
            "password": "testpass123",
            "name": "登录用户",
            "role": "job_seeker",
        },
    )
    # 再登录
    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "login@test.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    """登录密码错误"""
    await client.post(
        "/api/auth/register",
        json={
            "email": "wrongpw@test.com",
            "password": "testpass123",
            "name": "密码测试",
            "role": "job_seeker",
        },
    )
    resp = await client.post(
        "/api/auth/login",
        json={"email": "wrongpw@test.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """登录不存在的用户"""
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient) -> None:
    """刷新 token 成功"""
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "refresh@test.com",
            "password": "testpass123",
            "name": "刷新测试",
            "role": "job_seeker",
        },
    )
    refresh_token = reg_resp.json()["refresh_token"]

    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient) -> None:
    """刷新 token 无效"""
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient) -> None:
    """获取当前用户信息"""
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "me@test.com",
            "password": "testpass123",
            "name": "我的信息",
            "role": "job_seeker",
        },
    )
    token = reg_resp.json()["access_token"]

    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@test.com"
    assert data["name"] == "我的信息"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient) -> None:
    """未登录访问 /me"""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient) -> None:
    """登出成功"""
    reg_resp = await client.post(
        "/api/auth/register",
        json={
            "email": "logout@test.com",
            "password": "testpass123",
            "name": "登出用户",
            "role": "job_seeker",
        },
    )
    token = reg_resp.json()["access_token"]

    resp = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert "message" in resp.json()
