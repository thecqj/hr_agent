import io
import uuid

from app.api.deps import get_required_user
from app.main import app


def test_resume_parse_placeholder(client, seeker_user):
    app.dependency_overrides[get_required_user] = lambda: seeker_user

    files = {"file": ("resume.pdf", io.BytesIO(b"fake pdf bytes"), "application/pdf")}
    resp = client.post("/api/v1/resume/parse", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "skills" in data
    assert "self_evaluation" in data


def test_agent_chat_and_batch_and_evaluate_placeholder(client, recruiter_user):
    app.dependency_overrides[get_required_user] = lambda: recruiter_user

    chat_resp = client.post("/api/v1/agent/chat", json={"message": "hello"})
    assert chat_resp.status_code == 200
    assert "text/event-stream" in chat_resp.headers.get("content-type", "")

    batch_resp = client.post("/api/v1/agent/batch-screening", json=str(uuid.uuid4()))
    assert batch_resp.status_code == 200
    assert "status" in batch_resp.json()

    eval_resp = client.post(f"/api/v1/agent/evaluate/{uuid.uuid4()}")
    assert eval_resp.status_code == 200
    assert "message" in eval_resp.json()
