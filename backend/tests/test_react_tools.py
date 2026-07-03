"""ReAct Agent Tool 单元测试

对 7 个 Tool 进行纯单元测试，使用 AsyncMock 替代数据库，
不需要运行 PostgreSQL。
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.evaluation_task import EvaluationTask, EvalTaskStatus
from app.models.job import Job, JobStatus, WorkType
from app.models.user import User, UserRole


# ── Shared Constants & Helpers ───────────────────────────────

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


def _make_job(
    job_code: str = "J00001",
    title: str = "测试岗位",
    status: JobStatus = JobStatus.ACTIVE,
    work_type: WorkType = WorkType.ONSITE,
    head_count: int = 3,
    salary_min: int | None = 15000,
    salary_max: int | None = 30000,
    location: str | None = "北京",
    description: str = "岗位描述",
    requirements: str = "岗位要求",
    skills_required: list[str] | None = None,
) -> MagicMock:
    """Create a mock Job with sensible defaults."""
    job = MagicMock()
    job.id = uuid.uuid4()
    job.job_code = job_code
    job.title = title
    job.status = status
    job.work_type = work_type
    job.head_count = head_count
    job.salary_min = salary_min
    job.salary_max = salary_max
    job.location = location
    job.description = description
    job.requirements = requirements
    job.skills_required = skills_required or ["Python"]
    job.applications = []
    job.recruiter = MagicMock()
    job.recruiter.name = "测试招聘者"
    job.created_at = MagicMock()
    return job


def _make_user(
    user_id: uuid.UUID | None = None,
    name: str = "测试用户",
    role: UserRole = UserRole.RECRUITER,
) -> MagicMock:
    """Create a mock User."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.name = name
    user.role = role
    return user


def _make_application(
    applicant: MagicMock | None = None,
    status: ApplicationStatus = ApplicationStatus.PENDING,
    ai_score: float | None = 85.0,
    ai_decision: str | None = "recommend",
    ai_evaluation: str | None = None,
    ai_decision_reason: str | None = None,
    cover_letter: str | None = None,
    structured_resume: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock Application."""
    app = MagicMock()
    app.id = uuid.uuid4()
    app.applicant = applicant or _make_user(name="候选人张三")
    app.status = status
    app.ai_score = ai_score
    app.ai_decision = ai_decision
    app.ai_evaluation = ai_evaluation
    app.ai_decision_reason = ai_decision_reason
    app.cover_letter = cover_letter
    app.structured_resume = structured_resume
    app.created_at = MagicMock()
    return app


def _make_eval_task(
    status: EvalTaskStatus = EvalTaskStatus.COMPLETED,
    total_count: int = 10,
    evaluated_count: int = 10,
    result_summary: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> MagicMock:
    """Create a mock EvaluationTask."""
    task = MagicMock()
    task.id = uuid.uuid4()
    task.job_id = uuid.uuid4()
    task.triggered_by = uuid.UUID(TEST_USER_ID)
    task.status = status
    task.total_count = total_count
    task.evaluated_count = evaluated_count
    task.result_summary = result_summary
    task.error_message = error_message
    return task


_UNSET = object()  # Sentinel for "not provided" (distinguishes from None)


def _mock_result(
    scalars: list[Any] | None = None,
    one_or_none: Any = _UNSET,
    scalar: Any = _UNSET,
    all_rows: list[Any] | None = None,
) -> MagicMock:
    """Create a mock for SQLAlchemy Result.

    Supports: .scalars().all(), .scalar_one_or_none(), .scalar(), .all()
    """
    result = MagicMock()
    if scalars is not None:
        result.scalars.return_value.all.return_value = scalars
    if one_or_none is not _UNSET:
        result.scalar_one_or_none.return_value = one_or_none
    if scalar is not _UNSET:
        result.scalar.return_value = scalar
    if all_rows is not None:
        result.all.return_value = all_rows
    return result


# ── Shared Fixtures ──────────────────────────────────────────


@pytest.fixture
def mock_db() -> AsyncMock:
    """Mock AsyncSession that supports `async with` context manager."""
    db = AsyncMock(spec=AsyncSession)
    # Support `async with _get_db() as db:` pattern
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    return db


@pytest.fixture(autouse=True)
def mock_async_session(mock_db: AsyncMock) -> Any:
    """Mock async_session() to return a context-manager-compatible mock DB,
    and mock get_config() to inject user_id."""
    session_factory = MagicMock(return_value=mock_db)
    with patch(
        "app.database.async_session",
        session_factory,
    ), patch(
        "app.services.conversation.tools.get_config",
        return_value={"configurable": {"user_id": TEST_USER_ID}},
    ):
        yield


# ── query_jobs ───────────────────────────────────────────────


class TestQueryJobs:
    """query_jobs tool tests."""

    @pytest.mark.asyncio
    async def test_returns_jobs_with_default_fields(self, mock_db: AsyncMock) -> None:
        """query_jobs returns formatted job list with default fields."""
        from app.services.conversation.tools import query_jobs

        job = _make_job()
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({"filter": {"status": "active"}})

        assert isinstance(result, str)
        assert "J00001" in result
        assert "测试岗位" in result

    @pytest.mark.asyncio
    async def test_filters_by_job_code(self, mock_db: AsyncMock) -> None:
        """query_jobs with job_code filter returns matching job."""
        from app.services.conversation.tools import query_jobs

        job = _make_job(job_code="J04217", title="前端工程师")
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({"filter": {"job_code": "J04217"}})

        assert "J04217" in result
        assert "前端工程师" in result

    @pytest.mark.asyncio
    async def test_unknown_filter_key_ignored(self, mock_db: AsyncMock) -> None:
        """Unknown filter keys are silently ignored — no crash."""
        from app.services.conversation.tools import query_jobs

        job = _make_job()
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({"filter": {"evil_injection": "drop_tables"}})

        assert isinstance(result, str)
        assert "J00001" in result

    @pytest.mark.asyncio
    async def test_no_results_returns_not_found(self, mock_db: AsyncMock) -> None:
        """Empty result returns '未找到' message."""
        from app.services.conversation.tools import query_jobs

        mock_db.execute.return_value = _mock_result(scalars=[])

        result = await query_jobs.ainvoke({"filter": {"status": "active"}})

        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_custom_fields_in_output(self, mock_db: AsyncMock) -> None:
        """Requested fields appear in the output."""
        from app.services.conversation.tools import query_jobs

        job = _make_job(location="上海")
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({
            "filter": {"status": "active"},
            "fields": ["location", "salary_min", "salary_max"],
        })

        assert "上海" in result
        assert "15000" in result
        assert "30000" in result

    @pytest.mark.asyncio
    async def test_invalid_status_ignored(self, mock_db: AsyncMock) -> None:
        """An invalid status value is silently ignored — no crash."""
        from app.services.conversation.tools import query_jobs

        job = _make_job()
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({"filter": {"status": "nonexistent"}})

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_keyword_filter(self, mock_db: AsyncMock) -> None:
        """Keyword filter is applied (title fuzzy match)."""
        from app.services.conversation.tools import query_jobs

        job = _make_job(title="高级前端工程师")
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({"filter": {"keyword": "前端"}})

        assert "高级前端工程师" in result

    @pytest.mark.asyncio
    async def test_work_type_filter(self, mock_db: AsyncMock) -> None:
        """work_type filter with valid value is applied."""
        from app.services.conversation.tools import query_jobs

        job = _make_job(work_type=WorkType.REMOTE)
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({"filter": {"work_type": "remote"}, "fields": ["work_type"]})

        assert "remote" in result

    @pytest.mark.asyncio
    async def test_salary_range_filter(self, mock_db: AsyncMock) -> None:
        """Salary range filters are accepted without error."""
        from app.services.conversation.tools import query_jobs

        job = _make_job()
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({"filter": {"salary_min": 10000, "salary_max": 40000}})

        assert isinstance(result, str)
        assert "J00001" in result

    @pytest.mark.asyncio
    async def test_limit_capped_at_50(self, mock_db: AsyncMock) -> None:
        """Limit parameter is capped at 50."""
        from app.services.conversation.tools import query_jobs

        job = _make_job()
        mock_db.execute.return_value = _mock_result(scalars=[job])

        result = await query_jobs.ainvoke({"filter": {}, "limit": 999})

        # Should not crash — the SQL query uses min(limit, 50)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_recruiter_id_filter_applied(self, mock_db: AsyncMock) -> None:
        """query_jobs always scopes results by the authenticated user's recruiter_id."""
        from app.services.conversation.tools import query_jobs

        job = _make_job()
        mock_db.execute.return_value = _mock_result(scalars=[job])

        await query_jobs.ainvoke({"filter": {"status": "active"}})

        # Verify db.execute was called with a query whose WHERE clause
        # includes Job.recruiter_id == uuid.UUID(TEST_USER_ID).
        call_args = mock_db.execute.call_args
        assert call_args is not None
        compiled_sql = str(call_args[0][0].compile(compile_kwargs={"literal_binds": True}))
        # UUID is rendered without dashes in compiled SQL
        assert TEST_USER_ID.replace("-", "") in compiled_sql


# ── query_applications ───────────────────────────────────────


class TestQueryApplications:
    """query_applications tool tests."""

    @pytest.mark.asyncio
    async def test_no_job_returns_not_found(self, mock_db: AsyncMock) -> None:
        """Without job_code or job_title, resolve_job returns None -> not found."""
        from app.services.conversation.tools import query_applications

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=None):
            result = await query_applications.ainvoke({})

        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_group_by_status(self, mock_db: AsyncMock) -> None:
        """group_by=['status'] returns the hiring funnel."""
        from app.services.conversation.tools import query_applications

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools.count_by_job_grouped_by_status", new_callable=AsyncMock, return_value={"pending": 5, "interview": 2, "rejected": 1, "hired": 0}):
            result = await query_applications.ainvoke({
                "job_code": "J00001",
                "group_by": ["status"],
            })

        assert "待审核" in result
        assert "面试中" in result
        assert "5" in result

    @pytest.mark.asyncio
    async def test_group_by_ai_decision(self, mock_db: AsyncMock) -> None:
        """group_by=['ai_decision'] returns AI decision distribution."""
        from app.services.conversation.tools import query_applications

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(
                all_rows=[("recommend", 7), ("reject", 3)]
            )
            result = await query_applications.ainvoke({
                "job_code": "J00001",
                "group_by": ["ai_decision"],
            })

        assert "推荐" in result
        assert "不推荐" in result
        assert "7" in result

    @pytest.mark.asyncio
    async def test_group_by_cross(self, mock_db: AsyncMock) -> None:
        """group_by=['status','ai_decision'] returns cross-tab."""
        from app.services.conversation.tools import query_applications

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(
                all_rows=[(ApplicationStatus.PENDING, "recommend", 4)]
            )
            result = await query_applications.ainvoke({
                "job_code": "J00001",
                "group_by": ["status", "ai_decision"],
            })

        assert "待审核" in result
        assert "推荐" in result

    @pytest.mark.asyncio
    async def test_detail_query_with_filter(self, mock_db: AsyncMock) -> None:
        """Detail query returns formatted application list."""
        from app.services.conversation.tools import query_applications

        job = _make_job()
        applicant = _make_user(name="李四")
        app = _make_application(applicant=applicant, ai_score=92.0, ai_decision="recommend")
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(scalars=[app])
            result = await query_applications.ainvoke({
                "job_code": "J00001",
                "filter": {"ai_decision": "recommend"},
            })

        assert "李四" in result
        assert "92" in result

    @pytest.mark.asyncio
    async def test_multiple_jobs_match(self, mock_db: AsyncMock) -> None:
        """resolve_job returns a list -> 'multiple matches' message."""
        from app.services.conversation.tools import query_applications

        job1 = _make_job(job_code="J00001", title="前端1")
        job2 = _make_job(job_code="J00002", title="前端2")
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=[job1, job2]):
            result = await query_applications.ainvoke({"job_title": "前端"})

        assert "多个" in result
        assert "J00001" in result
        assert "J00002" in result

    @pytest.mark.asyncio
    async def test_no_matching_applications(self, mock_db: AsyncMock) -> None:
        """No applications for the job returns 'no records' message."""
        from app.services.conversation.tools import query_applications

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(scalars=[])
            result = await query_applications.ainvoke({
                "job_code": "J00001",
                "filter": {"status": "hired"},
            })

        assert "暂无匹配" in result

    @pytest.mark.asyncio
    async def test_invalid_group_by_ignored(self, mock_db: AsyncMock) -> None:
        """Invalid group_by values are silently ignored — falls through to detail query."""
        from app.services.conversation.tools import query_applications

        job = _make_job()
        app = _make_application()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(scalars=[app])
            result = await query_applications.ainvoke({
                "job_code": "J00001",
                "group_by": ["invalid_field"],
            })

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_resolve_job_receives_user_id(self, mock_db: AsyncMock) -> None:
        """resolve_job is called with the authenticated user_id for permission checking."""
        from app.services.conversation.tools import query_applications

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job) as mock_resolve:
            with patch("app.services.conversation.tools.count_by_job_grouped_by_status", new_callable=AsyncMock, return_value={"pending": 1}):
                await query_applications.ainvoke({
                    "job_code": "J00001",
                    "group_by": ["status"],
                })

        mock_resolve.assert_called_once()
        # Second positional arg is recruiter_id (= user_id from config)
        assert mock_resolve.call_args[0][1] == TEST_USER_ID


# ── query_evaluation ─────────────────────────────────────────


class TestQueryEvaluation:
    """query_evaluation tool tests."""

    @pytest.mark.asyncio
    async def test_by_task_id_found(self, mock_db: AsyncMock) -> None:
        """query_evaluation by task_id returns task summary."""
        from app.services.conversation.tools import query_evaluation

        task = _make_eval_task()
        mock_db.get.return_value = task

        result = await query_evaluation.ainvoke({"task_id": str(task.id)})

        assert "评估任务" in result
        assert "已完成" in result

    @pytest.mark.asyncio
    async def test_by_task_id_not_found(self, mock_db: AsyncMock) -> None:
        """Nonexistent task_id returns 'not found' message."""
        from app.services.conversation.tools import query_evaluation

        mock_db.get.return_value = None

        result = await query_evaluation.ainvoke({"task_id": str(uuid.uuid4())})

        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_by_task_id_no_permission(self, mock_db: AsyncMock) -> None:
        """Task belonging to another user returns 'no permission' message."""
        from app.services.conversation.tools import query_evaluation

        task = _make_eval_task()
        task.triggered_by = uuid.uuid4()  # Different from TEST_USER_ID
        mock_db.get.return_value = task

        result = await query_evaluation.ainvoke({"task_id": str(task.id)})

        assert "无权" in result

    @pytest.mark.asyncio
    async def test_by_job_code_found(self, mock_db: AsyncMock) -> None:
        """query_evaluation by job_code returns latest task."""
        from app.services.conversation.tools import query_evaluation

        job = _make_job()
        task = _make_eval_task()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(one_or_none=task)
            result = await query_evaluation.ainvoke({"job_code": "J00001"})

        assert "评估任务" in result

    @pytest.mark.asyncio
    async def test_by_job_code_no_task(self, mock_db: AsyncMock) -> None:
        """Job exists but no evaluation task -> 'not found'."""
        from app.services.conversation.tools import query_evaluation

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(one_or_none=None)
            result = await query_evaluation.ainvoke({"job_code": "J00001"})

        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_by_job_code_multiple_jobs(self, mock_db: AsyncMock) -> None:
        """Multiple jobs match job_code -> 'multiple matches' message."""
        from app.services.conversation.tools import query_evaluation

        job1 = _make_job(job_code="J00001")
        job2 = _make_job(job_code="J00002")
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=[job1, job2]):
            result = await query_evaluation.ainvoke({"job_code": "J00001"})

        assert "多个" in result

    @pytest.mark.asyncio
    async def test_no_identifiers_returns_not_found(self, mock_db: AsyncMock) -> None:
        """No task_id and no job_code -> 'not found'."""
        from app.services.conversation.tools import query_evaluation

        result = await query_evaluation.ainvoke({})

        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_with_result_summary(self, mock_db: AsyncMock) -> None:
        """Task with result_summary includes recommendation counts."""
        from app.services.conversation.tools import query_evaluation

        task = _make_eval_task(
            result_summary={"recommend_count": 6, "reject_count": 4, "cutoff_score": 75.0}
        )
        mock_db.get.return_value = task

        result = await query_evaluation.ainvoke({"task_id": str(task.id)})

        assert "推荐" in result
        assert "6" in result
        assert "截止分数" in result

    @pytest.mark.asyncio
    async def test_with_error_message(self, mock_db: AsyncMock) -> None:
        """Task with error_message includes the error in output."""
        from app.services.conversation.tools import query_evaluation

        task = _make_eval_task(status=EvalTaskStatus.FAILED, error_message="API 超时")
        mock_db.get.return_value = task

        result = await query_evaluation.ainvoke({"task_id": str(task.id)})

        assert "失败" in result
        assert "API 超时" in result


# ── trigger_evaluation ───────────────────────────────────────


class TestTriggerEvaluation:
    """trigger_evaluation tool tests."""

    @pytest.mark.asyncio
    async def test_job_not_found(self, mock_db: AsyncMock) -> None:
        """resolve_job returns None -> 'not found'."""
        from app.services.conversation.tools import trigger_evaluation

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=None):
            result = await trigger_evaluation.ainvoke({"job_code": "J00001"})

        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_multiple_jobs_match(self, mock_db: AsyncMock) -> None:
        """Multiple matching jobs -> 'specify job code' message."""
        from app.services.conversation.tools import trigger_evaluation

        job1 = _make_job(job_code="J00001", title="前端1")
        job2 = _make_job(job_code="J00002", title="前端2")
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=[job1, job2]):
            result = await trigger_evaluation.ainvoke({"job_title": "前端"})

        assert "多个" in result

    @pytest.mark.asyncio
    async def test_existing_running_task(self, mock_db: AsyncMock) -> None:
        """An existing PENDING/RUNNING task blocks new evaluation."""
        from app.services.conversation.tools import trigger_evaluation

        job = _make_job()
        existing_task = _make_eval_task(status=EvalTaskStatus.RUNNING)
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(one_or_none=existing_task)
            result = await trigger_evaluation.ainvoke({"job_code": "J00001"})

        assert "已有" in result or "正在进行" in result

    @pytest.mark.asyncio
    async def test_no_pending_applications(self, mock_db: AsyncMock) -> None:
        """Zero pending applications -> 'cannot trigger' message."""
        from app.services.conversation.tools import trigger_evaluation

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            # First execute: existing task check -> None; Second: pending count -> 0
            mock_db.execute.side_effect = [
                _mock_result(one_or_none=None),
                _mock_result(scalar=0),
            ]
            result = await trigger_evaluation.ainvoke({"job_code": "J00001"})

        assert "暂无待处理" in result

    @pytest.mark.asyncio
    async def test_success(self, mock_db: AsyncMock) -> None:
        """Successful evaluation trigger returns completion summary."""
        from app.services.conversation.tools import trigger_evaluation

        job = _make_job()
        completed_task = _make_eval_task(
            status=EvalTaskStatus.COMPLETED,
            result_summary={"recommend_count": 3, "reject_count": 2},
        )

        async def _mock_events() -> Any:
            yield {"event": "on_custom_event", "data": {"status": "evaluating"}}
            return

        mock_graph = MagicMock()
        mock_graph.astream_events.return_value = _mock_events()

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools.adispatch_custom_event", new_callable=AsyncMock), \
             patch("app.database.get_checkpointer", return_value=MagicMock()), \
             patch("app.services.agent.graph.build_evaluation_graph", return_value=mock_graph):
            # execute calls: 1) existing task check, 2) pending count
            mock_db.execute.side_effect = [
                _mock_result(one_or_none=None),
                _mock_result(scalar=5),
            ]
            # db.get returns the completed task after graph runs
            mock_db.get.return_value = completed_task

            result = await trigger_evaluation.ainvoke({"job_code": "J00001"})

        assert "评估完成" in result
        assert "推荐" in result
        assert "3" in result

    @pytest.mark.asyncio
    async def test_graph_error(self, mock_db: AsyncMock) -> None:
        """Graph execution error is caught and reported."""
        from app.services.conversation.tools import trigger_evaluation

        job = _make_job()
        pending_task = _make_eval_task(status=EvalTaskStatus.PENDING)

        mock_graph = MagicMock()
        mock_graph.astream_events.side_effect = RuntimeError("Graph crashed")

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools.adispatch_custom_event", new_callable=AsyncMock), \
             patch("app.database.get_checkpointer", return_value=MagicMock()), \
             patch("app.services.agent.graph.build_evaluation_graph", return_value=mock_graph):
            mock_db.execute.side_effect = [
                _mock_result(one_or_none=None),
                _mock_result(scalar=3),
            ]
            # db.get called in error handler to check task status
            mock_db.get.return_value = pending_task

            result = await trigger_evaluation.ainvoke({"job_code": "J00001"})

        assert "出错" in result or "异常" in result
        assert "Graph crashed" in result

    @pytest.mark.asyncio
    async def test_resolve_job_receives_user_id(self, mock_db: AsyncMock) -> None:
        """resolve_job is called with the authenticated user_id for permission checking."""
        from app.services.conversation.tools import trigger_evaluation

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job) as mock_resolve:
            mock_db.execute.side_effect = [
                _mock_result(one_or_none=None),
                _mock_result(scalar=0),
            ]
            await trigger_evaluation.ainvoke({"job_code": "J00001"})

        mock_resolve.assert_called_once()
        assert mock_resolve.call_args[0][1] == TEST_USER_ID


# ── confirm_evaluation ───────────────────────────────────────


class TestConfirmEvaluation:
    """confirm_evaluation tool tests."""

    @pytest.mark.asyncio
    async def test_task_not_found(self, mock_db: AsyncMock) -> None:
        """Nonexistent task_id -> 'task not found' message."""
        from app.services.conversation.tools import confirm_evaluation

        mock_db.get.return_value = None

        result = await confirm_evaluation.ainvoke({"task_id": str(uuid.uuid4())})

        assert "不存在" in result

    @pytest.mark.asyncio
    async def test_no_permission(self, mock_db: AsyncMock) -> None:
        """Task belonging to another user -> 'no permission'."""
        from app.services.conversation.tools import confirm_evaluation

        task = _make_eval_task()
        task.triggered_by = uuid.uuid4()  # Different from TEST_USER_ID
        mock_db.get.return_value = task

        result = await confirm_evaluation.ainvoke({"task_id": str(task.id)})

        assert "无权" in result

    @pytest.mark.asyncio
    async def test_wrong_status(self, mock_db: AsyncMock) -> None:
        """Task not in COMPLETED status -> status error."""
        from app.services.conversation.tools import confirm_evaluation

        task = _make_eval_task(status=EvalTaskStatus.RUNNING)
        mock_db.get.return_value = task

        result = await confirm_evaluation.ainvoke({"task_id": str(task.id)})

        assert "只有 completed" in result

    @pytest.mark.asyncio
    async def test_user_not_found(self, mock_db: AsyncMock) -> None:
        """User not found in DB -> 'user not found' message."""
        from app.services.conversation.tools import confirm_evaluation

        task = _make_eval_task()

        def _get_side_effect(model: Any, pk: Any) -> Any:
            if model is EvaluationTask:
                return task
            return None

        mock_db.get.side_effect = _get_side_effect

        result = await confirm_evaluation.ainvoke({"task_id": str(task.id)})

        assert "用户不存在" in result

    @pytest.mark.asyncio
    async def test_success(self, mock_db: AsyncMock) -> None:
        """Successful confirmation updates candidate statuses."""
        from app.services.conversation.tools import confirm_evaluation

        task = _make_eval_task()
        user = _make_user()
        recommend_app = _make_application(status=ApplicationStatus.PENDING, ai_decision="recommend")
        reject_app = _make_application(status=ApplicationStatus.PENDING, ai_decision="reject")

        def _get_side_effect(model: Any, pk: Any) -> Any:
            if model is EvaluationTask:
                return task
            if model is User:
                return user
            return None

        mock_db.get.side_effect = _get_side_effect

        # Two execute calls: recommend apps, reject apps
        mock_db.execute.side_effect = [
            _mock_result(scalars=[recommend_app]),
            _mock_result(scalars=[reject_app]),
        ]

        result = await confirm_evaluation.ainvoke({"task_id": str(task.id)})

        assert "已确认" in result
        assert "2" in result  # 1 recommend + 1 reject = 2 updated
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_success_no_applications(self, mock_db: AsyncMock) -> None:
        """Confirmation with zero pending applications updates 0 candidates."""
        from app.services.conversation.tools import confirm_evaluation

        task = _make_eval_task()
        user = _make_user()

        def _get_side_effect(model: Any, pk: Any) -> Any:
            if model is EvaluationTask:
                return task
            if model is User:
                return user
            return None

        mock_db.get.side_effect = _get_side_effect
        mock_db.execute.side_effect = [
            _mock_result(scalars=[]),
            _mock_result(scalars=[]),
        ]

        result = await confirm_evaluation.ainvoke({"task_id": str(task.id)})

        assert "已确认" in result
        assert "0" in result


# ── update_candidate_status ──────────────────────────────────


class TestUpdateCandidateStatus:
    """update_candidate_status tool tests."""

    @pytest.mark.asyncio
    async def test_invalid_target_status(self) -> None:
        """Invalid target_status (e.g. 'hired') is rejected."""
        from app.services.conversation.tools import update_candidate_status

        result = await update_candidate_status.ainvoke({
            "job_code": "J00001",
            "candidate_name": "张三",
            "target_status": "hired",
        })

        assert "只接受" in result

    @pytest.mark.asyncio
    async def test_job_not_found(self, mock_db: AsyncMock) -> None:
        """resolve_job returns None -> 'not found'."""
        from app.services.conversation.tools import update_candidate_status

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=None):
            result = await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "张三",
                "target_status": "interview",
            })

        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_multiple_jobs_match(self, mock_db: AsyncMock) -> None:
        """Multiple matching jobs -> 'specify unique' message."""
        from app.services.conversation.tools import update_candidate_status

        job1 = _make_job(job_code="J00001")
        job2 = _make_job(job_code="J00002")
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=[job1, job2]):
            result = await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "张三",
                "target_status": "interview",
            })

        assert "多个" in result

    @pytest.mark.asyncio
    async def test_candidate_not_found(self, mock_db: AsyncMock) -> None:
        """No matching candidate -> 'not found' message."""
        from app.services.conversation.tools import update_candidate_status

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(scalars=[])
            result = await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "不存在的候选人",
                "target_status": "interview",
            })

        assert "未找到候选人" in result

    @pytest.mark.asyncio
    async def test_multiple_candidates_same_name(self, mock_db: AsyncMock) -> None:
        """Multiple candidates with same name -> 'provide more info' message."""
        from app.services.conversation.tools import update_candidate_status

        job = _make_job()
        app1 = _make_application(applicant=_make_user(name="张三"))
        app2 = _make_application(applicant=_make_user(name="张三"))
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(scalars=[app1, app2])
            result = await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "张三",
                "target_status": "interview",
            })

        assert "更精确" in result

    @pytest.mark.asyncio
    async def test_success_interview(self, mock_db: AsyncMock) -> None:
        """Successful status update to 'interview'."""
        from app.services.conversation.tools import update_candidate_status

        job = _make_job()
        applicant = _make_user(name="李四")
        app = _make_application(applicant=applicant)
        user = _make_user()

        def _get_side_effect(model: Any, pk: Any) -> Any:
            if model is User:
                return user
            return None

        mock_db.get.side_effect = _get_side_effect

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools.update_application_status", new_callable=AsyncMock, return_value=app):
            mock_db.execute.return_value = _mock_result(scalars=[app])
            result = await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "李四",
                "target_status": "interview",
            })

        assert "面试阶段" in result
        assert "李四" in result

    @pytest.mark.asyncio
    async def test_success_rejected(self, mock_db: AsyncMock) -> None:
        """Successful status update to 'rejected'."""
        from app.services.conversation.tools import update_candidate_status

        job = _make_job()
        applicant = _make_user(name="王五")
        app = _make_application(applicant=applicant)
        user = _make_user()

        def _get_side_effect(model: Any, pk: Any) -> Any:
            if model is User:
                return user
            return None

        mock_db.get.side_effect = _get_side_effect

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools.update_application_status", new_callable=AsyncMock, return_value=app):
            mock_db.execute.return_value = _mock_result(scalars=[app])
            result = await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "王五",
                "target_status": "rejected",
            })

        assert "已拒绝" in result
        assert "王五" in result

    @pytest.mark.asyncio
    async def test_service_exception(self, mock_db: AsyncMock) -> None:
        """Service function raises -> error message returned."""
        from app.services.conversation.tools import update_candidate_status

        job = _make_job()
        applicant = _make_user(name="赵六")
        app = _make_application(applicant=applicant)
        user = _make_user()

        def _get_side_effect(model: Any, pk: Any) -> Any:
            if model is User:
                return user
            return None

        mock_db.get.side_effect = _get_side_effect

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools.update_application_status", new_callable=AsyncMock, side_effect=RuntimeError("DB error")):
            mock_db.execute.return_value = _mock_result(scalars=[app])
            result = await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "赵六",
                "target_status": "interview",
            })

        assert "失败" in result
        assert "DB error" in result

    @pytest.mark.asyncio
    async def test_user_not_found(self, mock_db: AsyncMock) -> None:
        """Current user not in DB -> 'user not found' message."""
        from app.services.conversation.tools import update_candidate_status

        job = _make_job()
        applicant = _make_user(name="张三")
        app = _make_application(applicant=applicant)

        def _get_side_effect(model: Any, pk: Any) -> Any:
            return None  # No user found

        mock_db.get.side_effect = _get_side_effect

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            mock_db.execute.return_value = _mock_result(scalars=[app])
            result = await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "张三",
                "target_status": "interview",
            })

        assert "用户不存在" in result

    @pytest.mark.asyncio
    async def test_resolve_job_receives_user_id(self, mock_db: AsyncMock) -> None:
        """resolve_job is called with the authenticated user_id for permission checking."""
        from app.services.conversation.tools import update_candidate_status

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job) as mock_resolve:
            mock_db.execute.return_value = _mock_result(scalars=[])
            await update_candidate_status.ainvoke({
                "job_code": "J00001",
                "candidate_name": "张三",
                "target_status": "interview",
            })

        mock_resolve.assert_called_once()
        assert mock_resolve.call_args[0][1] == TEST_USER_ID


# ── update_job_status ────────────────────────────────────────


class TestUpdateJobStatus:
    """update_job_status tool tests."""

    @pytest.mark.asyncio
    async def test_invalid_target_status(self) -> None:
        """Invalid target_status (e.g. 'draft') is rejected."""
        from app.services.conversation.tools import update_job_status

        result = await update_job_status.ainvoke({
            "job_code": "J00001",
            "target_status": "draft",
        })

        assert "只接受" in result

    @pytest.mark.asyncio
    async def test_job_not_found(self, mock_db: AsyncMock) -> None:
        """resolve_job returns None -> 'not found'."""
        from app.services.conversation.tools import update_job_status

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=None):
            result = await update_job_status.ainvoke({
                "job_code": "J00001",
                "target_status": "active",
            })

        assert "未找到" in result

    @pytest.mark.asyncio
    async def test_multiple_jobs_match(self, mock_db: AsyncMock) -> None:
        """Multiple matching jobs -> 'specify unique' message."""
        from app.services.conversation.tools import update_job_status

        job1 = _make_job(job_code="J00001")
        job2 = _make_job(job_code="J00002")
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=[job1, job2]):
            result = await update_job_status.ainvoke({
                "job_code": "J00001",
                "target_status": "active",
            })

        assert "多个" in result

    @pytest.mark.asyncio
    async def test_success_active(self, mock_db: AsyncMock) -> None:
        """Successful status update to 'active'."""
        from app.services.conversation.tools import update_job_status

        job = _make_job()
        user = _make_user()
        mock_db.get.return_value = user

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools._update_job_status_svc", new_callable=AsyncMock, return_value=job):
            result = await update_job_status.ainvoke({
                "job_code": "J00001",
                "target_status": "active",
            })

        assert "开启" in result
        assert "J00001" in result

    @pytest.mark.asyncio
    async def test_success_closed(self, mock_db: AsyncMock) -> None:
        """Successful status update to 'closed'."""
        from app.services.conversation.tools import update_job_status

        job = _make_job()
        user = _make_user()
        mock_db.get.return_value = user

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools._update_job_status_svc", new_callable=AsyncMock, return_value=job):
            result = await update_job_status.ainvoke({
                "job_code": "J00001",
                "target_status": "closed",
            })

        assert "关闭" in result

    @pytest.mark.asyncio
    async def test_user_not_found(self, mock_db: AsyncMock) -> None:
        """Current user not in DB -> 'user not found' message."""
        from app.services.conversation.tools import update_job_status

        job = _make_job()
        mock_db.get.return_value = None

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job):
            result = await update_job_status.ainvoke({
                "job_code": "J00001",
                "target_status": "active",
            })

        assert "用户不存在" in result

    @pytest.mark.asyncio
    async def test_service_exception(self, mock_db: AsyncMock) -> None:
        """Service function raises -> error message returned."""
        from app.services.conversation.tools import update_job_status

        job = _make_job()
        user = _make_user()
        mock_db.get.return_value = user

        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.tools._update_job_status_svc", new_callable=AsyncMock, side_effect=PermissionError("not owner")):
            result = await update_job_status.ainvoke({
                "job_code": "J00001",
                "target_status": "closed",
            })

        assert "失败" in result
        assert "not owner" in result

    @pytest.mark.asyncio
    async def test_resolve_job_receives_user_id(self, mock_db: AsyncMock) -> None:
        """resolve_job is called with the authenticated user_id for permission checking."""
        from app.services.conversation.tools import update_job_status

        job = _make_job()
        with patch("app.services.conversation.tools.resolve_job", new_callable=AsyncMock, return_value=job) as mock_resolve:
            mock_db.get.return_value = None
            await update_job_status.ainvoke({
                "job_code": "J00001",
                "target_status": "active",
            })

        mock_resolve.assert_called_once()
        assert mock_resolve.call_args[0][1] == TEST_USER_ID


# ── _sanitize_filter ──────────────────────────────────────────


class TestSanitizeFilter:
    """_sanitize_filter security whitelist tests."""

    def test_strips_unknown_keys(self) -> None:
        """Unknown keys are stripped; only whitelisted keys survive."""
        from app.services.conversation.tools import _sanitize_filter, _JOBS_FILTER_KEYS

        raw = {"job_code": "J001", "evil": "drop", "status": "active"}
        result = _sanitize_filter(raw, _JOBS_FILTER_KEYS)
        assert result == {"job_code": "J001", "status": "active"}

    def test_returns_empty_for_none(self) -> None:
        """None input returns empty dict."""
        from app.services.conversation.tools import _sanitize_filter, _JOBS_FILTER_KEYS

        result = _sanitize_filter(None, _JOBS_FILTER_KEYS)
        assert result == {}

    def test_returns_empty_for_empty(self) -> None:
        """Empty dict input returns empty dict."""
        from app.services.conversation.tools import _sanitize_filter, _JOBS_FILTER_KEYS

        result = _sanitize_filter({}, _JOBS_FILTER_KEYS)
        assert result == {}

