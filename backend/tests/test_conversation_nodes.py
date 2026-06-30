"""对话 Agent 节点测试"""

import uuid
from typing import Any

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.agent import IntentResult
from app.models.job import Job, JobStatus
from app.models.application import Application, ApplicationStatus
from app.models.user import User
from app.services.conversation.state import ConversationState
from app.services.conversation.nodes import (
    intent_node,
    feedback_node,
    route_by_intent,
    route_by_pending_action,
    list_jobs_node,
    job_detail_node,
    pending_count_node,
    interview_count_node,
    candidate_eval_node,
    funnel_node,
    candidate_list_node,
    confirm_node,
    cancel_node,
    status_change_node,
    job_status_action_node,
)


class TestIntentNode:
    """intent_node 测试"""

    @pytest.mark.asyncio
    async def test_evaluate_intent(self) -> None:
        """测试识别 evaluate 意图"""
        mock_result = IntentResult(
            intent="evaluate",
            confidence=0.9,
            extracted_params={"job_title": "前端开发"},
        )
        mock_provider = AsyncMock()
        mock_provider.recognize_intent = AsyncMock(return_value=mock_result)
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "帮我筛选前端开发岗位的简历",
            "current_user_id": "test-user",
            "errors": [],
        }

        with patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ), patch(
            "app.services.conversation.nodes.adispatch_custom_event",
            new_callable=AsyncMock,
        ):
            result = await intent_node(state)

        assert result["intent"] == "evaluate"
        assert result["extracted_params"]["job_title"] == "前端开发"

    @pytest.mark.asyncio
    async def test_help_intent(self) -> None:
        """测试识别 help 意图"""
        mock_result = IntentResult(
            intent="help",
            confidence=0.95,
            extracted_params={},
        )
        mock_provider = AsyncMock()
        mock_provider.recognize_intent = AsyncMock(return_value=mock_result)
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "你能做什么",
            "current_user_id": "test-user",
            "errors": [],
        }

        with patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ), patch(
            "app.services.conversation.nodes.adispatch_custom_event",
            new_callable=AsyncMock,
        ):
            result = await intent_node(state)

        assert result["intent"] == "help"

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self) -> None:
        """测试 LLM 失败时回退为 unknown"""
        mock_provider = AsyncMock()
        mock_provider.recognize_intent = AsyncMock(side_effect=Exception("API error"))
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "测试消息",
            "current_user_id": "test-user",
            "errors": [],
        }

        with patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ), patch(
            "app.services.conversation.nodes.adispatch_custom_event",
            new_callable=AsyncMock,
        ):
            result = await intent_node(state)

        assert result["intent"] == "unknown"
        assert result.get("clarifying_question") is not None


class TestFeedbackNode:
    """feedback_node 测试"""

    @pytest.mark.asyncio
    async def test_help_feedback(self) -> None:
        """测试 help 意图的反馈"""
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "test-user",
            "intent": "help",
            "errors": [],
            "chat_history": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert "岗位管理" in result["reply_message"]
        assert "chat_history" in result

    @pytest.mark.asyncio
    async def test_unknown_feedback(self) -> None:
        """测试 unknown 意图的反馈"""
        state: ConversationState = {
            "user_message": "天气怎么样",
            "current_user_id": "test-user",
            "intent": "unknown",
            "clarifying_question": "请问您想执行什么操作？",
            "errors": [],
            "chat_history": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert "请问您想执行什么操作" in result["reply_message"]
        assert "chat_history" in result

    @pytest.mark.asyncio
    async def test_pre_set_reply_message(self) -> None:
        """测试 dispatch 已设置 reply_message 时不覆盖"""
        state: ConversationState = {
            "user_message": "筛选简历",
            "current_user_id": "test-user",
            "intent": "evaluate",
            "reply_message": "❌ 未找到匹配的岗位。",
            "errors": [],
            "chat_history": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        # reply_message 已存在，feedback_node 应保留并附带 chat_history
        assert result["reply_message"] == "❌ 未找到匹配的岗位。"
        assert "chat_history" in result


class TestRouteByIntent:
    """route_by_intent 测试"""

    def test_evaluate_routes_to_dispatch(self) -> None:
        state: ConversationState = {"intent": "evaluate"}
        assert route_by_intent(state) == "dispatch"

    def test_list_jobs_routes_to_list_jobs(self) -> None:
        state: ConversationState = {"intent": "list_jobs"}
        assert route_by_intent(state) == "list_jobs"

    def test_job_detail_routes_to_job_detail(self) -> None:
        state: ConversationState = {"intent": "job_detail"}
        assert route_by_intent(state) == "job_detail"

    def test_pending_count_routes_to_pending_count(self) -> None:
        state: ConversationState = {"intent": "pending_count"}
        assert route_by_intent(state) == "pending_count"

    def test_interview_count_routes_to_interview_count(self) -> None:
        state: ConversationState = {"intent": "interview_count"}
        assert route_by_intent(state) == "interview_count"

    def test_candidate_eval_routes_to_candidate_eval(self) -> None:
        state: ConversationState = {"intent": "candidate_eval"}
        assert route_by_intent(state) == "candidate_eval"

    def test_funnel_routes_to_funnel(self) -> None:
        state: ConversationState = {"intent": "funnel"}
        assert route_by_intent(state) == "funnel"

    def test_candidate_list_routes_to_candidate_list(self) -> None:
        state: ConversationState = {"intent": "candidate_list"}
        assert route_by_intent(state) == "candidate_list"

    def test_status_change_routes_to_confirm(self) -> None:
        state: ConversationState = {"intent": "status_change"}
        assert route_by_intent(state) == "confirm"

    def test_job_status_routes_to_confirm(self) -> None:
        state: ConversationState = {"intent": "job_status"}
        assert route_by_intent(state) == "confirm"

    def test_confirm_routes_to_execute_action(self) -> None:
        state: ConversationState = {"intent": "confirm", "pending_action": {"intent": "status_change", "params": {}}}
        assert route_by_intent(state) == "execute_action"

    def test_confirm_without_pending_routes_to_feedback(self) -> None:
        state: ConversationState = {"intent": "confirm"}
        assert route_by_intent(state) == "feedback"

    def test_cancel_routes_to_cancel(self) -> None:
        state: ConversationState = {"intent": "cancel"}
        assert route_by_intent(state) == "cancel"

    def test_help_routes_to_feedback(self) -> None:
        state: ConversationState = {"intent": "help"}
        assert route_by_intent(state) == "feedback"

    def test_unknown_routes_to_feedback(self) -> None:
        state: ConversationState = {"intent": "unknown"}
        assert route_by_intent(state) == "feedback"

    def test_default_routes_to_feedback(self) -> None:
        state: ConversationState = {}
        assert route_by_intent(state) == "feedback"


class TestRouteByPendingAction:
    """route_by_pending_action 测试"""

    def test_status_change_action(self) -> None:
        state: ConversationState = {"pending_action": {"intent": "status_change", "params": {}}}
        assert route_by_pending_action(state) == "status_change"

    def test_job_status_action(self) -> None:
        state: ConversationState = {"pending_action": {"intent": "job_status", "params": {}}}
        assert route_by_pending_action(state) == "job_status_action"

    def test_no_pending_action(self) -> None:
        state: ConversationState = {}
        assert route_by_pending_action(state) == "feedback"

    def test_unknown_action(self) -> None:
        state: ConversationState = {"pending_action": {"intent": "unknown", "params": {}}}
        assert route_by_pending_action(state) == "feedback"


# ── Query Node Test Helpers ──────────────────────────────────────


def _make_job(
    job_code: str = "J04217",
    title: str = "前端开发",
    status: JobStatus = JobStatus.ACTIVE,
) -> MagicMock:
    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.job_code = job_code
    job.title = title
    job.status = status
    job.recruiter_id = uuid.uuid4()
    job.description = "负责前端开发"
    job.requirements = "3年经验"
    job.skills_required = ["React", "TypeScript"]
    job.salary_min = 20000
    job.salary_max = 40000
    job.location = "北京"
    job.work_type = MagicMock()
    job.work_type.value = "hybrid"
    job.head_count = 3
    job.interview_quota = 5
    return job


# ── Query Node Tests ─────────────────────────────────────────────


class TestListJobsNode:
    @pytest.mark.asyncio
    async def test_list_active_jobs(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        state: ConversationState = {
            "user_message": "有哪些活跃岗位？",
            "current_user_id": recruiter_id,
            "intent": "list_jobs",
            "extracted_params": {"status_filter": "active"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.svc_list_jobs", new_callable=AsyncMock, return_value=([job], 1)):
            result = await list_jobs_node(state)

        assert "前端开发" in result["reply_message"]
        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "job_list"


class TestJobDetailNode:
    @pytest.mark.asyncio
    async def test_job_detail_full(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217详情",
            "current_user_id": recruiter_id,
            "intent": "job_detail",
            "extracted_params": {"job_code": "J04217", "detail_scope": "full"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job):
            result = await job_detail_node(state)

        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "job_detail"

    @pytest.mark.asyncio
    async def test_job_detail_not_found(self) -> None:
        recruiter_id = str(uuid.uuid4())
        state: ConversationState = {
            "user_message": "J99999详情",
            "current_user_id": recruiter_id,
            "intent": "job_detail",
            "extracted_params": {"job_code": "J99999"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=None):
            result = await job_detail_node(state)

        assert "未找到" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_job_detail_disambiguation(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job1 = _make_job(job_code="J04217", title="前端开发工程师")
        job2 = _make_job(job_code="J04218", title="前端架构师")
        state: ConversationState = {
            "user_message": "前端岗位详情",
            "current_user_id": recruiter_id,
            "intent": "job_detail",
            "extracted_params": {"job_title": "前端"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=[job1, job2]):
            result = await job_detail_node(state)

        assert "多个" in result["reply_message"] or "指定" in result["reply_message"]


class TestPendingCountNode:
    @pytest.mark.asyncio
    async def test_pending_count(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217还有多少简历没看？",
            "current_user_id": recruiter_id,
            "intent": "pending_count",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.count_by_job_and_status", new_callable=AsyncMock, return_value=7):
            result = await pending_count_node(state)

        assert "7" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_pending_count_zero(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217还有多少简历没看？",
            "current_user_id": recruiter_id,
            "intent": "pending_count",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.count_by_job_and_status", new_callable=AsyncMock, return_value=0):
            result = await pending_count_node(state)

        assert "暂无" in result["reply_message"]


class TestInterviewCountNode:
    @pytest.mark.asyncio
    async def test_interview_count(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217有几个人在面试？",
            "current_user_id": recruiter_id,
            "intent": "interview_count",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.count_by_job_and_status", new_callable=AsyncMock, return_value=3):
            result = await interview_count_node(state)

        assert "3" in result["reply_message"]


class TestCandidateEvalNode:
    @pytest.mark.asyncio
    async def test_candidate_eval_found(self) -> None:
        recruiter_id = str(uuid.uuid4())
        mock_app = MagicMock(spec=Application)
        mock_app.ai_score = 85.5
        mock_app.ai_decision = "recommend"
        mock_app.ai_decision_reason = "技术能力强"
        mock_app.ai_evaluation = {"summary": "优秀候选人"}
        mock_app.status = ApplicationStatus.PENDING
        applicant = MagicMock()
        applicant.name = "张三"
        mock_app.applicant = applicant

        state: ConversationState = {
            "user_message": "张三的评估结果",
            "current_user_id": recruiter_id,
            "intent": "candidate_eval",
            "extracted_params": {"candidate_name": "张三", "application_id": "app-123"},
        }

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_app)
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db):
            result = await candidate_eval_node(state)

        assert "85.5" in result["reply_message"] or "推荐" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_candidate_eval_not_found(self) -> None:
        recruiter_id = str(uuid.uuid4())
        state: ConversationState = {
            "user_message": "某某的评估结果",
            "current_user_id": recruiter_id,
            "intent": "candidate_eval",
            "extracted_params": {"candidate_name": "某某", "application_id": "nonexistent"},
        }

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db):
            result = await candidate_eval_node(state)

        assert "未找到" in result["reply_message"]


class TestFunnelNode:
    @pytest.mark.asyncio
    async def test_funnel(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217招聘进度",
            "current_user_id": recruiter_id,
            "intent": "funnel",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        grouped = {"pending": 10, "interview": 3, "rejected": 5}
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.count_by_job_grouped_by_status", new_callable=AsyncMock, return_value=grouped):
            result = await funnel_node(state)

        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "funnel"


class TestCandidateListNode:
    @pytest.mark.asyncio
    async def test_candidate_list(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        mock_app = MagicMock(spec=Application)
        mock_app.ai_score = 85.5
        mock_app.ai_decision = "recommend"
        mock_app.status = ApplicationStatus.PENDING
        applicant = MagicMock()
        applicant.name = "张三"
        mock_app.applicant = applicant

        state: ConversationState = {
            "user_message": "J04217推荐的候选人",
            "current_user_id": recruiter_id,
            "intent": "candidate_list",
            "extracted_params": {"job_code": "J04217", "decision_filter": "recommended"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.list_by_job", new_callable=AsyncMock, return_value=[mock_app]):
            result = await candidate_list_node(state)

        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "candidate_list"

    @pytest.mark.asyncio
    async def test_candidate_list_empty(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        state: ConversationState = {
            "user_message": "J04217推荐的候选人",
            "current_user_id": recruiter_id,
            "intent": "candidate_list",
            "extracted_params": {"job_code": "J04217"},
        }

        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.list_by_job", new_callable=AsyncMock, return_value=[]):
            result = await candidate_list_node(state)

        assert "暂无" in result["reply_message"] or "没有" in result["reply_message"]


# ── Confirm / Action Flow Tests ──────────────────────────────────


class TestConfirmNode:
    @pytest.mark.asyncio
    async def test_confirm_sets_pending_action(self) -> None:
        state: ConversationState = {
            "user_message": "把张三推进到面试阶段",
            "current_user_id": str(uuid.uuid4()),
            "intent": "status_change",
            "extracted_params": {"candidate_name": "张三", "target_status": "interview"},
        }
        with patch("app.services.conversation.nodes.adispatch_custom_event", new_callable=AsyncMock):
            result = await confirm_node(state)
        assert result.get("pending_action") is not None
        assert result["pending_action"]["intent"] == "status_change"
        assert result["reply_cards"] is not None
        assert result["reply_cards"][0]["type"] == "confirm"

    @pytest.mark.asyncio
    async def test_confirm_for_job_status(self) -> None:
        state: ConversationState = {
            "user_message": "关闭J04217",
            "current_user_id": str(uuid.uuid4()),
            "intent": "job_status",
            "extracted_params": {"job_code": "J04217", "action": "close"},
        }
        with patch("app.services.conversation.nodes.adispatch_custom_event", new_callable=AsyncMock):
            result = await confirm_node(state)
        assert result.get("pending_action") is not None
        assert result["pending_action"]["intent"] == "job_status"


class TestConfirmNodeResolution:
    """confirm_node application_id resolution tests"""

    @pytest.mark.asyncio
    async def test_confirm_resolves_application_id(self) -> None:
        """confirm_node resolves candidate_name to application_id when job_code provided"""
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        mock_app = MagicMock(spec=Application)
        mock_app.id = uuid.uuid4()
        mock_app.status = ApplicationStatus.PENDING
        mock_app.ai_score = 85.0
        mock_app.ai_decision = "recommend"
        applicant = MagicMock()
        applicant.name = "张三"
        mock_app.applicant = applicant

        state: ConversationState = {
            "user_message": "把张三推进到面试",
            "current_user_id": recruiter_id,
            "intent": "status_change",
            "extracted_params": {"candidate_name": "张三", "target_status": "interview", "job_code": "J04217"},
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_app]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.adispatch_custom_event", new_callable=AsyncMock):
            result = await confirm_node(state)

        # Should have resolved application_id
        assert result["pending_action"]["params"].get("application_id") is not None
        assert result["pending_action"]["params"]["application_id"] == str(mock_app.id)

    @pytest.mark.asyncio
    async def test_confirm_with_existing_application_id(self) -> None:
        """confirm_node uses existing application_id if already in params"""
        state: ConversationState = {
            "user_message": "确认操作",
            "current_user_id": str(uuid.uuid4()),
            "intent": "status_change",
            "extracted_params": {"candidate_name": "张三", "target_status": "interview", "application_id": "app-123"},
        }

        with patch("app.services.conversation.nodes.adispatch_custom_event", new_callable=AsyncMock):
            result = await confirm_node(state)

        assert result["pending_action"]["params"]["application_id"] == "app-123"

    @pytest.mark.asyncio
    async def test_confirm_disambiguates_multiple_candidates(self) -> None:
        """confirm_node returns disambiguation message when multiple candidates match"""
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)

        app1 = MagicMock(spec=Application)
        app1.id = uuid.uuid4()
        app2 = MagicMock(spec=Application)
        app2.id = uuid.uuid4()

        state: ConversationState = {
            "user_message": "把张三推进到面试",
            "current_user_id": recruiter_id,
            "intent": "status_change",
            "extracted_params": {"candidate_name": "张三", "target_status": "interview", "job_code": "J04217"},
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [app1, app2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.adispatch_custom_event", new_callable=AsyncMock):
            result = await confirm_node(state)

        # Should return disambiguation message, not pending_action
        assert "多个" in result["reply_message"] or "指定" in result["reply_message"]
        assert "pending_action" not in result

    @pytest.mark.asyncio
    async def test_confirm_no_match_returns_error(self) -> None:
        """confirm_node returns error when no candidate found"""
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)

        state: ConversationState = {
            "user_message": "把张三推进到面试",
            "current_user_id": recruiter_id,
            "intent": "status_change",
            "extracted_params": {"candidate_name": "张三", "target_status": "interview", "job_code": "J04217"},
        }

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.adispatch_custom_event", new_callable=AsyncMock):
            result = await confirm_node(state)

        assert "未找到" in result["reply_message"]
        assert "pending_action" not in result


class TestCancelNode:
    @pytest.mark.asyncio
    async def test_cancel_clears_pending_action(self) -> None:
        state: ConversationState = {
            "user_message": "取消",
            "current_user_id": str(uuid.uuid4()),
            "intent": "cancel",
            "pending_action": {"intent": "status_change", "params": {"candidate_name": "张三", "target_status": "interview"}},
        }
        result = await cancel_node(state)
        assert result.get("pending_action") is None
        assert "取消" in result["reply_message"]


class TestStatusChangeNode:
    @pytest.mark.asyncio
    async def test_status_change_executes(self) -> None:
        recruiter_id = str(uuid.uuid4())
        mock_app = MagicMock(spec=Application)
        mock_app.id = uuid.uuid4()
        mock_app.status = ApplicationStatus.INTERVIEW
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": recruiter_id,
            "intent": "confirm",
            "pending_action": {
                "intent": "status_change",
                "params": {
                    "application_id": str(mock_app.id),
                    "target_status": "interview",
                    "candidate_name": "张三",
                },
            },
        }
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=MagicMock(spec=User))
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.update_application_status", new_callable=AsyncMock, return_value=mock_app):
            result = await status_change_node(state)
        assert "面试" in result["reply_message"]
        assert "张三" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_status_change_no_pending_action(self) -> None:
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": str(uuid.uuid4()),
            "intent": "confirm",
            "pending_action": None,
        }
        result = await status_change_node(state)
        assert result["pending_action"] is None
        assert "没有" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_status_change_missing_application_id(self) -> None:
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": str(uuid.uuid4()),
            "intent": "confirm",
            "pending_action": {
                "intent": "status_change",
                "params": {"target_status": "interview", "candidate_name": "张三"},
            },
        }
        result = await status_change_node(state)
        assert result["pending_action"] is None
        assert "缺少" in result["reply_message"]


class TestJobStatusActionNode:
    @pytest.mark.asyncio
    async def test_job_close(self) -> None:
        recruiter_id = str(uuid.uuid4())
        job = _make_job()
        job.recruiter_id = uuid.UUID(recruiter_id)
        job.status = JobStatus.CLOSED
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": recruiter_id,
            "intent": "confirm",
            "pending_action": {
                "intent": "job_status",
                "params": {"job_code": "J04217", "action": "close"},
            },
        }
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=MagicMock(spec=User))
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=job), \
             patch("app.services.conversation.nodes.update_job_status", new_callable=AsyncMock, return_value=job):
            result = await job_status_action_node(state)
        assert "关闭" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_job_status_action_no_pending_action(self) -> None:
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": str(uuid.uuid4()),
            "intent": "confirm",
            "pending_action": None,
        }
        result = await job_status_action_node(state)
        assert result["pending_action"] is None
        assert "没有" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_job_status_action_job_not_found(self) -> None:
        recruiter_id = str(uuid.uuid4())
        state: ConversationState = {
            "user_message": "确认",
            "current_user_id": recruiter_id,
            "intent": "confirm",
            "pending_action": {
                "intent": "job_status",
                "params": {"job_code": "J99999", "action": "close"},
            },
        }
        mock_db = AsyncMock()
        with patch("app.services.conversation.nodes._get_db", return_value=mock_db), \
             patch("app.services.conversation.nodes.resolve_job", new_callable=AsyncMock, return_value=None):
            result = await job_status_action_node(state)
        assert result["pending_action"] is None
        assert "未找到" in result["reply_message"]


class TestPendingActionEdgeCase:
    @pytest.mark.asyncio
    async def test_new_intent_clears_pending_action(self) -> None:
        """用户有待确认操作时发出新意图，应隐式取消"""
        state: ConversationState = {
            "user_message": "有哪些岗位？",
            "current_user_id": "u1",
            "intent": "list_jobs",
            "extracted_params": {"status_filter": "active"},
            "pending_action": {"intent": "status_change", "params": {"candidate_name": "张三"}},
            "reply_message": "共 2 个岗位：",
            "chat_history": [],
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert result.get("pending_action") is None
        assert "已取消待确认操作" in result.get("reply_message", "")


class TestFeedbackNodeExtended:
    @pytest.mark.asyncio
    async def test_list_jobs_feedback(self) -> None:
        """list_jobs already set reply_message, feedback preserves it with chat_history"""
        state: ConversationState = {
            "user_message": "有哪些岗位？",
            "current_user_id": "u1",
            "intent": "list_jobs",
            "reply_message": "共 3 个岗位：",
            "reply_cards": [{"type": "job_list", "jobs": []}],
            "chat_history": [],
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)
        # feedback_node now returns reply_message + chat_history instead of empty dict
        assert result["reply_message"] == "共 3 个岗位："
        assert "chat_history" in result
        assert result["chat_history"][0]["role"] == "user"
        assert result["chat_history"][1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_pending_action_cleared_on_new_intent(self) -> None:
        """When pending_action exists but user sends new intent, feedback clears it"""
        state: ConversationState = {
            "user_message": "有哪些岗位？",
            "current_user_id": "u1",
            "intent": "list_jobs",
            "pending_action": {"intent": "status_change", "params": {}},
            "reply_message": "共 3 个岗位：",
            "chat_history": [],
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)
        assert "pending_action" in result
        assert result["pending_action"] is None
        assert "已取消待确认操作" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_cancel_without_pending_action(self) -> None:
        """cancel intent with no pending_action returns fallback message"""
        state: ConversationState = {
            "user_message": "取消",
            "current_user_id": "u1",
            "intent": "cancel",
            "errors": [],
            "chat_history": [],
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)
        assert "已取消" in result["reply_message"]
        assert "chat_history" in result

    @pytest.mark.asyncio
    async def test_help_feedback_updated(self) -> None:
        """help intent feedback should mention all new features"""
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "u1",
            "intent": "help",
            "chat_history": [],
        }
        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)
        assert "岗位管理" in result["reply_message"]
        assert "招聘进度" in result["reply_message"]
        assert "候选人管理" in result["reply_message"]
        assert "简历筛选" in result["reply_message"]
        assert "chat_history" in result


class TestMultiTurnIntentRecognition:
    """多轮对话上下文感知意图识别"""

    @pytest.mark.asyncio
    async def test_context_entities_filled_in_extracted_params(self) -> None:
        """当 context_entities 有 current_job_code 但 extracted_params 没有 job_code 时，应补全"""
        mock_result = IntentResult(
            intent="pending_count",
            confidence=0.9,
            extracted_params={},  # No job_code from LLM
        )
        mock_provider = AsyncMock()
        mock_provider.recognize_intent = AsyncMock(return_value=mock_result)
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "还有多少简历",
            "current_user_id": "test-user",
            "context_entities": {"current_job_id": "job-123", "current_job_code": "J04217"},
            "errors": [],
        }

        with patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ), patch(
            "app.services.conversation.nodes.adispatch_custom_event",
            new_callable=AsyncMock,
        ):
            result = await intent_node(state)

        # job_code should be filled from context_entities
        assert result["extracted_params"]["job_code"] == "J04217"
        assert result["extracted_params"]["job_id"] == "job-123"

    @pytest.mark.asyncio
    async def test_context_prompt_built_from_state(self) -> None:
        """_build_context_prompt should return non-None when state has context"""
        from app.services.conversation.nodes import _build_context_prompt

        state: ConversationState = {
            "user_message": "筛选这些简历",
            "current_user_id": "test-user",
            "context_entities": {"current_job_id": "job-123", "current_job_code": "J04217"},
            "errors": [],
        }
        context = _build_context_prompt(state)
        assert context is not None
        assert "J04217" in context

    @pytest.mark.asyncio
    async def test_context_prompt_none_when_no_context(self) -> None:
        """无上下文时 _build_context_prompt 返回 None"""
        from app.services.conversation.nodes import _build_context_prompt

        state: ConversationState = {
            "user_message": "筛选简历",
            "current_user_id": "test-user",
            "errors": [],
        }
        context = _build_context_prompt(state)
        assert context is None

    @pytest.mark.asyncio
    async def test_context_prompt_includes_session_summary(self) -> None:
        """session_summary 应出现在上下文提示词中"""
        from app.services.conversation.nodes import _build_context_prompt

        state: ConversationState = {
            "user_message": "那个岗位有多少简历",
            "current_user_id": "test-user",
            "session_summary": "用户之前讨论了前端开发岗位 J04217 的简历筛选",
            "errors": [],
        }
        context = _build_context_prompt(state)
        assert context is not None
        assert "前端开发" in context

    @pytest.mark.asyncio
    async def test_context_prompt_includes_recent_history(self) -> None:
        """最近对话历史应出现在上下文提示词中"""
        from app.services.conversation.nodes import _build_context_prompt

        state: ConversationState = {
            "user_message": "筛选这些简历",
            "current_user_id": "test-user",
            "chat_history": [
                {"role": "user", "content": "J001有多少简历", "timestamp": 1.0},
                {"role": "assistant", "content": "J001有5份待审核简历", "timestamp": 2.0},
            ],
            "errors": [],
        }
        context = _build_context_prompt(state)
        assert context is not None
        assert "J001" in context

    @pytest.mark.asyncio
    async def test_existing_params_not_overridden_by_context(self) -> None:
        """LLM 识别出的参数不应被 context_entities 覆盖"""
        mock_result = IntentResult(
            intent="pending_count",
            confidence=0.9,
            extracted_params={"job_code": "J99999"},  # LLM identified this
        )
        mock_provider = AsyncMock()
        mock_provider.recognize_intent = AsyncMock(return_value=mock_result)
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "J99999有多少简历",
            "current_user_id": "test-user",
            "context_entities": {"current_job_code": "J04217"},
            "errors": [],
        }

        with patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ), patch(
            "app.services.conversation.nodes.adispatch_custom_event",
            new_callable=AsyncMock,
        ):
            result = await intent_node(state)

        # LLM's result should NOT be overridden
        assert result["extracted_params"]["job_code"] == "J99999"


class TestFeedbackNodeHistory:
    """feedback_node 的对话历史和摘要逻辑"""

    @pytest.mark.asyncio
    async def test_feedback_appends_to_chat_history(self) -> None:
        """feedback_node 应将当前轮次追加到 chat_history"""
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "test-user",
            "intent": "help",
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert "chat_history" in result
        assert len(result["chat_history"]) == 2  # user + assistant
        assert result["chat_history"][0]["role"] == "user"
        assert result["chat_history"][1]["role"] == "assistant"
        assert result["chat_history"][0]["content"] == "帮助"

    @pytest.mark.asyncio
    async def test_feedback_preserves_existing_history(self) -> None:
        """feedback_node 应保留已有的 chat_history"""
        existing = [
            {"role": "user", "content": "你好", "timestamp": 1.0},
            {"role": "assistant", "content": "你好！", "timestamp": 2.0},
        ]
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "test-user",
            "intent": "help",
            "chat_history": existing,
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert len(result["chat_history"]) == 4  # 2 existing + 2 new
        assert result["chat_history"][0]["content"] == "你好"
        assert result["chat_history"][2]["content"] == "帮助"

    @pytest.mark.asyncio
    async def test_feedback_summary_triggered_when_history_exceeds_threshold(self) -> None:
        """chat_history 超过阈值时应触发摘要压缩"""
        # Build 12 turns of history (> 10 threshold)
        history: list[dict[str, Any]] = []
        for i in range(12):
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"消息 {i}",
                "timestamp": float(i),
            })

        mock_provider = AsyncMock()
        mock_provider.summarize_conversation = AsyncMock(return_value="压缩后的摘要")
        mock_provider.close = AsyncMock()

        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "test-user",
            "intent": "help",
            "chat_history": history,
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"), patch(
            "app.services.conversation.nodes._get_llm_provider",
            return_value=mock_provider,
        ):
            result = await feedback_node(state)

        # Summary should have been generated
        assert result["session_summary"] == "压缩后的摘要"
        # History should be truncated (first 5 removed, then 2 new added = 12-5+2=9)
        assert len(result["chat_history"]) == 9

    @pytest.mark.asyncio
    async def test_feedback_no_summary_when_history_below_threshold(self) -> None:
        """chat_history 未超过阈值时不应触发摘要压缩"""
        state: ConversationState = {
            "user_message": "帮助",
            "current_user_id": "test-user",
            "intent": "help",
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        # No summary should be generated
        assert result.get("session_summary") is None
