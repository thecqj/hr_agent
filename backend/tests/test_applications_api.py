import uuid
from datetime import datetime
from types import SimpleNamespace

from app.api.deps import get_required_user
from app.main import app
from app.models.application import ApplicationStatus


def _mock_application(applicant_id=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        applicant_id=applicant_id or uuid.uuid4(),
        applicant=SimpleNamespace(name="候选人A"),
        resume_text="简历内容",
        cover_letter="求职信",
        match_score=None,
        ai_suggestions=None,
        structured_resume=None,
        status=ApplicationStatus.PENDING,
        created_at=datetime.utcnow(),
    )


def test_applications_endpoints(client, seeker_user, recruiter_user, monkeypatch):
    from app.api.v1 import applications as app_api

    async def _create(_db, _data, user, force=False):
        return _mock_application(applicant_id=user.id)

    async def _my(_db, user, page=1, page_size=20):
        return [_mock_application(applicant_id=user.id)], 1

    async def _for_job(_db, _job_id, _user, status_filter=None, page=1, page_size=20):
        return [_mock_application()], 1

    async def _update_status(_db, _application_id, _data, _user):
        return _mock_application()

    monkeypatch.setattr(app_api.application_service, "create_application", _create)
    monkeypatch.setattr(app_api.application_service, "get_my_applications", _my)
    monkeypatch.setattr(app_api.application_service, "get_applications_for_job", _for_job)
    monkeypatch.setattr(app_api.application_service, "update_application_status", _update_status)

    app.dependency_overrides[get_required_user] = lambda: seeker_user

    create_resp = client.post(
        "/api/v1/applications/",
        json={"job_id": str(uuid.uuid4()), "resume_text": "abc", "cover_letter": "hi"},
    )
    assert create_resp.status_code == 201

    my_resp = client.get("/api/v1/applications/my")
    assert my_resp.status_code == 200
    assert my_resp.json()["total"] == 1

    app.dependency_overrides[get_required_user] = lambda: recruiter_user

    job_resp = client.get(f"/api/v1/applications/job/{uuid.uuid4()}")
    assert job_resp.status_code == 200

    update_resp = client.patch(
        f"/api/v1/applications/{uuid.uuid4()}/status",
        json={"status": "reviewed"},
    )
    assert update_resp.status_code == 200
