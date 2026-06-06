import uuid
from types import SimpleNamespace

from app.api.deps import get_optional_user, get_required_user
from app.main import app
from app.models.job import JobStatus, WorkType


def _mock_job(recruiter_id=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        recruiter_id=recruiter_id or uuid.uuid4(),
        title="Python后端",
        description="负责后端开发",
        salary_min=15,
        salary_max=25,
        location="上海",
        work_type=WorkType.ONSITE,
        skills_required=["Python", "FastAPI"],
        status=JobStatus.ACTIVE,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        applications_count=0,
    )


def test_jobs_endpoints(client, recruiter_user, monkeypatch):
    from app.api.v1 import jobs as jobs_api

    async def _create(_db, _data, user):
        return _mock_job(recruiter_id=user.id)

    async def _list(*args, **kwargs):
        return [_mock_job()], 1

    async def _get(_db, _job_id):
        return _mock_job()

    async def _update(_db, _job_id, _data, user):
        return _mock_job(recruiter_id=user.id)

    async def _delete(_db, _job_id, _user):
        return None

    async def _update_status(_db, _job_id, _data, user):
        return _mock_job(recruiter_id=user.id)

    monkeypatch.setattr(jobs_api.job_service, "create_job", _create)
    monkeypatch.setattr(jobs_api.job_service, "list_jobs", _list)
    monkeypatch.setattr(jobs_api.job_service, "get_job", _get)
    monkeypatch.setattr(jobs_api.job_service, "update_job", _update)
    monkeypatch.setattr(jobs_api.job_service, "delete_job", _delete)
    monkeypatch.setattr(jobs_api.job_service, "update_job_status", _update_status)

    app.dependency_overrides[get_required_user] = lambda: recruiter_user
    app.dependency_overrides[get_optional_user] = lambda: recruiter_user

    create_resp = client.post(
        "/api/v1/jobs/",
        json={
            "title": "Python后端",
            "description": "负责后端开发",
            "salary_min": 15,
            "salary_max": 25,
            "location": "上海",
            "work_type": "onsite",
            "skills_required": ["Python", "FastAPI"],
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["title"] == "Python后端"

    list_resp = client.get("/api/v1/jobs/")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1

    detail_resp = client.get("/api/v1/jobs/some-job-id")
    assert detail_resp.status_code == 200

    update_resp = client.put("/api/v1/jobs/some-job-id", json={"title": "新标题"})
    assert update_resp.status_code == 200

    status_resp = client.patch("/api/v1/jobs/some-job-id/status", json={"status": "active"})
    assert status_resp.status_code == 200

    delete_resp = client.delete("/api/v1/jobs/some-job-id")
    assert delete_resp.status_code == 200
    assert "message" in delete_resp.json()
