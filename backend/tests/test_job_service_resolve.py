"""Job Service resolve_job 辅助方法测试"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_service import resolve_job


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    return db


class TestResolveJob:
    @pytest.mark.asyncio
    async def test_exact_match_by_job_code(self, mock_db: AsyncMock) -> None:
        mock_job = MagicMock()
        mock_job.recruiter_id = uuid.uuid4()
        mock_job.job_code = "J04217"
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_scalar

        result = await resolve_job(mock_db, str(mock_job.recruiter_id), job_code="J04217")
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_fuzzy_match_by_title_single_result(self, mock_db: AsyncMock) -> None:
        recruiter_id = uuid.uuid4()
        mock_job = MagicMock()
        mock_job.recruiter_id = recruiter_id
        mock_job.title = "前端开发工程师"
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_job]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await resolve_job(mock_db, str(recruiter_id), job_title_keyword="前端")
        assert result == mock_job

    @pytest.mark.asyncio
    async def test_fuzzy_match_multiple_results(self, mock_db: AsyncMock) -> None:
        recruiter_id = uuid.uuid4()
        mock_job1 = MagicMock()
        mock_job1.recruiter_id = recruiter_id
        mock_job2 = MagicMock()
        mock_job2.recruiter_id = recruiter_id
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_job1, mock_job2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await resolve_job(mock_db, str(recruiter_id), job_title_keyword="开发")
        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self, mock_db: AsyncMock) -> None:
        recruiter_id = uuid.uuid4()
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_scalar

        # job_code path
        result = await resolve_job(mock_db, str(recruiter_id), job_code="J99999")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_params_returns_none(self, mock_db: AsyncMock) -> None:
        recruiter_id = uuid.uuid4()
        result = await resolve_job(mock_db, str(recruiter_id))
        assert result is None

    @pytest.mark.asyncio
    async def test_job_code_wrong_recruiter_returns_none(self, mock_db: AsyncMock) -> None:
        mock_job = MagicMock()
        mock_job.recruiter_id = uuid.uuid4()  # different recruiter
        mock_job.job_code = "J04217"
        mock_scalar = MagicMock()
        mock_scalar.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_scalar

        result = await resolve_job(mock_db, str(uuid.uuid4()), job_code="J04217")
        assert result is None
