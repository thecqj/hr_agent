import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# 确保可以从 backend 根目录导入 app 包
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.deps import get_optional_user, get_required_user
from app.database import get_db
from app.main import app
from app.models.user import UserRole


@pytest.fixture(autouse=True)
def _reset_overrides():
    app.dependency_overrides.clear()

    async def _fake_db():
        yield None

    app.dependency_overrides[get_db] = _fake_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeker_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="seeker@example.com",
        name="Seeker",
        role=UserRole.JOB_SEEKER,
        phone=None,
        avatar_url=None,
        is_active=True,
    )


@pytest.fixture
def recruiter_user():
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="recruiter@example.com",
        name="Recruiter",
        role=UserRole.RECRUITER,
        phone=None,
        avatar_url=None,
        is_active=True,
    )


def override_required_user(user):
    def _dep():
        return user

    app.dependency_overrides[get_required_user] = _dep


def override_optional_user(user=None):
    def _dep():
        return user

    app.dependency_overrides[get_optional_user] = _dep
