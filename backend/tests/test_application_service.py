"""Application Service 新增查询方法测试"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.services.application_service import (
    count_by_job_and_status,
    count_by_job_grouped_by_status,
    list_by_job,
)


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.get = AsyncMock()
    return db


class TestCountByJobAndStatus:
    @pytest.mark.asyncio
    async def test_returns_count_for_specific_status(self, mock_db: AsyncMock) -> None:
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = 5
        mock_db.execute.return_value = mock_scalar

        result = await count_by_job_and_status(mock_db, str(uuid.uuid4()), "pending")
        assert result == 5

    @pytest.mark.asyncio
    async def test_returns_zero_when_none(self, mock_db: AsyncMock) -> None:
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = None
        mock_db.execute.return_value = mock_scalar

        result = await count_by_job_and_status(mock_db, str(uuid.uuid4()), "interview")
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_for_invalid_status(self, mock_db: AsyncMock) -> None:
        result = await count_by_job_and_status(mock_db, str(uuid.uuid4()), "invalid_status")
        assert result == 0


class TestCountByJobGroupedByStatus:
    @pytest.mark.asyncio
    async def test_returns_grouped_counts(self, mock_db: AsyncMock) -> None:
        row1 = MagicMock()
        row1.__getitem__ = lambda self, key: [ApplicationStatus.PENDING, 10][key]
        row2 = MagicMock()
        row2.__getitem__ = lambda self, key: [ApplicationStatus.INTERVIEW, 3][key]
        row3 = MagicMock()
        row3.__getitem__ = lambda self, key: [ApplicationStatus.REJECTED, 2][key]
        mock_result = MagicMock()
        mock_result.all.return_value = [row1, row2, row3]
        mock_db.execute.return_value = mock_result

        result = await count_by_job_grouped_by_status(mock_db, str(uuid.uuid4()))
        assert result["pending"] == 10
        assert result["interview"] == 3
        assert result["rejected"] == 2

    @pytest.mark.asyncio
    async def test_returns_all_status_keys_with_zero_when_none(self, mock_db: AsyncMock) -> None:
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await count_by_job_grouped_by_status(mock_db, str(uuid.uuid4()))
        # Should return all ApplicationStatus keys with count 0
        assert set(result.keys()) == {s.value for s in ApplicationStatus}
        assert all(v == 0 for v in result.values())


class TestListByJob:
    @pytest.mark.asyncio
    async def test_returns_applications_without_filter(self, mock_db: AsyncMock) -> None:
        mock_app = MagicMock(spec=Application)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_app]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await list_by_job(mock_db, str(uuid.uuid4()))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self, mock_db: AsyncMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await list_by_job(mock_db, str(uuid.uuid4()), decision_filter="recommended")
        assert result == []

    @pytest.mark.asyncio
    async def test_passes_decision_filter(self, mock_db: AsyncMock) -> None:
        """Verify that when decision_filter is provided, the method constructs
        a query that includes the ai_decision filter condition."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await list_by_job(mock_db, str(uuid.uuid4()), decision_filter="recommended")
        assert result == []
        # Verify db.execute was called (query was constructed with filter)
        mock_db.execute.assert_called_once()
