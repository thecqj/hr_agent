def test_register_login_refresh_and_me(client, seeker_user, monkeypatch):
    from app.api.v1 import auth as auth_api
    from app.main import app

    async def _register(_db, _data):
        return {
            "access_token": "a",
            "refresh_token": "r",
            "token_type": "bearer",
            "expires_in": 1800,
            "user": {
                "id": str(seeker_user.id),
                "email": seeker_user.email,
                "name": seeker_user.name,
                "role": seeker_user.role.value,
                "phone": seeker_user.phone,
                "avatar_url": seeker_user.avatar_url,
                "is_active": True,
            },
        }

    async def _login(_db, _email, _password):
        return {
            "access_token": "a2",
            "refresh_token": "r2",
            "token_type": "bearer",
            "expires_in": 1800,
            "user": {
                "id": str(seeker_user.id),
                "email": seeker_user.email,
                "name": seeker_user.name,
                "role": seeker_user.role.value,
                "phone": seeker_user.phone,
                "avatar_url": seeker_user.avatar_url,
                "is_active": True,
            },
        }

    async def _refresh(_db, _token):
        return {
            "access_token": "a3",
            "refresh_token": "r3",
            "token_type": "bearer",
            "expires_in": 1800,
        }

    monkeypatch.setattr(auth_api.auth_service, "register_user", _register)
    monkeypatch.setattr(auth_api.auth_service, "login_user", _login)
    monkeypatch.setattr(auth_api.auth_service, "refresh_access_token", _refresh)

    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "seeker@example.com",
            "password": "123456",
            "name": "Seeker",
            "role": "job_seeker",
            "phone": None,
        },
    )
    assert register_resp.status_code == 200
    assert register_resp.json()["user"]["email"] == "seeker@example.com"

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "seeker@example.com", "password": "123456"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["access_token"] == "a2"

    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "token"})
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["access_token"] == "a3"

    from app.api.deps import get_required_user

    app.dependency_overrides[get_required_user] = lambda: seeker_user

    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "job_seeker"

    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200
    assert "message" in logout_resp.json()
