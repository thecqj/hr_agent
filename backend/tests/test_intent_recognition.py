"""意图识别测试"""

import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.agent import IntentResult


class TestIntentResultSchema:
    """IntentResult schema 验证测试"""

    def test_evaluate_intent(self) -> None:
        result = IntentResult(
            intent="evaluate",
            confidence=0.9,
            extracted_params={"job_title": "前端开发"},
        )
        assert result.intent == "evaluate"
        assert result.confidence == 0.9
        assert result.extracted_params["job_title"] == "前端开发"

    def test_help_intent(self) -> None:
        result = IntentResult(
            intent="help",
            confidence=0.95,
            extracted_params={},
        )
        assert result.intent == "help"

    def test_unknown_intent_with_question(self) -> None:
        result = IntentResult(
            intent="unknown",
            confidence=0.3,
            extracted_params={},
            clarifying_question="请问您想执行什么操作？",
        )
        assert result.intent == "unknown"
        assert result.clarifying_question is not None

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception):
            IntentResult(intent="evaluate", confidence=1.5, extracted_params={})
        with pytest.raises(Exception):
            IntentResult(intent="evaluate", confidence=-0.1, extracted_params={})

    def test_invalid_intent(self) -> None:
        with pytest.raises(Exception):
            IntentResult(intent="invalid", confidence=0.5, extracted_params={})

    def test_list_jobs_intent(self) -> None:
        result = IntentResult(
            intent="list_jobs",
            confidence=0.9,
            extracted_params={"status_filter": "active"},
        )
        assert result.intent == "list_jobs"
        assert result.extracted_params["status_filter"] == "active"

    def test_job_detail_intent(self) -> None:
        result = IntentResult(
            intent="job_detail",
            confidence=0.88,
            extracted_params={"job_code": "J04217", "detail_scope": "requirements"},
        )
        assert result.intent == "job_detail"

    def test_pending_count_intent(self) -> None:
        result = IntentResult(
            intent="pending_count",
            confidence=0.92,
            extracted_params={"job_code": "J04217"},
        )
        assert result.intent == "pending_count"

    def test_interview_count_intent(self) -> None:
        result = IntentResult(
            intent="interview_count",
            confidence=0.91,
            extracted_params={"job_title": "前端开发"},
        )
        assert result.intent == "interview_count"

    def test_candidate_eval_intent(self) -> None:
        result = IntentResult(
            intent="candidate_eval",
            confidence=0.87,
            extracted_params={"candidate_name": "张三", "job_code": "J04217"},
        )
        assert result.intent == "candidate_eval"

    def test_funnel_intent(self) -> None:
        result = IntentResult(
            intent="funnel",
            confidence=0.90,
            extracted_params={"job_code": "J04217"},
        )
        assert result.intent == "funnel"

    def test_candidate_list_intent(self) -> None:
        result = IntentResult(
            intent="candidate_list",
            confidence=0.89,
            extracted_params={"job_code": "J04217", "decision_filter": "recommended"},
        )
        assert result.intent == "candidate_list"

    def test_status_change_intent(self) -> None:
        result = IntentResult(
            intent="status_change",
            confidence=0.85,
            extracted_params={"candidate_name": "张三", "target_status": "interview"},
        )
        assert result.intent == "status_change"

    def test_job_status_intent(self) -> None:
        result = IntentResult(
            intent="job_status",
            confidence=0.93,
            extracted_params={"job_code": "J04217", "action": "close"},
        )
        assert result.intent == "job_status"

    def test_confirm_intent(self) -> None:
        result = IntentResult(
            intent="confirm",
            confidence=0.95,
            extracted_params={},
        )
        assert result.intent == "confirm"

    def test_cancel_intent(self) -> None:
        result = IntentResult(
            intent="cancel",
            confidence=0.95,
            extracted_params={},
        )
        assert result.intent == "cancel"


class TestIntentRecognitionProvider:
    """DeepSeekProvider.recognize_intent 集成测试（mock LLM 响应）"""

    @pytest.mark.asyncio
    async def test_recognize_evaluate_intent(self) -> None:
        """测试识别 evaluate 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "evaluate",
            "confidence": 0.92,
            "extracted_params": {"job_title": "前端开发"},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("帮我筛选前端开发岗位的简历")
            assert result.intent == "evaluate"
            assert result.extracted_params.get("job_title") == "前端开发"
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_evaluate_with_quota(self) -> None:
        """测试识别带进面人数的 evaluate 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "evaluate",
            "confidence": 0.88,
            "extracted_params": {"job_title": "前端", "interview_quota": 5},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("前端岗位选5个人进面试")
            assert result.intent == "evaluate"
            assert result.extracted_params.get("interview_quota") == 5
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_help_intent(self) -> None:
        """测试识别 help 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "help",
            "confidence": 0.95,
            "extracted_params": {},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("你能做什么")
            assert result.intent == "help"
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_unknown_intent(self) -> None:
        """测试识别 unknown 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "unknown",
            "confidence": 0.4,
            "extracted_params": {},
            "clarifying_question": "请问您想执行什么操作？",
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("今天天气怎么样")
            assert result.intent == "unknown"
            assert result.clarifying_question is not None
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_list_jobs_intent(self) -> None:
        """测试识别 list_jobs 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "list_jobs",
            "confidence": 0.9,
            "extracted_params": {"status_filter": "active"},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("现在有哪些活跃岗位？")
            assert result.intent == "list_jobs"
            assert result.extracted_params.get("status_filter") == "active"
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_job_detail_intent(self) -> None:
        """测试识别 job_detail 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "job_detail",
            "confidence": 0.88,
            "extracted_params": {"job_code": "J04217", "detail_scope": "requirements"},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("J04217的任职要求是什么？")
            assert result.intent == "job_detail"
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_status_change_intent(self) -> None:
        """测试识别 status_change 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "status_change",
            "confidence": 0.85,
            "extracted_params": {"candidate_name": "张三", "target_status": "interview"},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("把张三推进到面试阶段")
            assert result.intent == "status_change"
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_confirm_intent(self) -> None:
        """测试识别 confirm 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "confirm",
            "confidence": 0.95,
            "extracted_params": {},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("确认")
            assert result.intent == "confirm"
        await provider.close()

    @pytest.mark.asyncio
    async def test_recognize_cancel_intent(self) -> None:
        """测试识别 cancel 意图"""
        from app.llm.deepseek import DeepSeekProvider

        mock_response = {
            "intent": "cancel",
            "confidence": 0.95,
            "extracted_params": {},
        }

        provider = DeepSeekProvider()
        with patch.object(provider, "_call_chat", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.recognize_intent("取消")
            assert result.intent == "cancel"
        await provider.close()
