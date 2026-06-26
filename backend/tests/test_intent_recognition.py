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
