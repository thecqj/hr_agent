"""对话 Agent 节点测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.agent import IntentResult
from app.services.conversation.state import ConversationState
from app.services.conversation.nodes import (
    intent_node,
    feedback_node,
    route_by_intent,
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
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert "筛选岗位简历" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_unknown_feedback(self) -> None:
        """测试 unknown 意图的反馈"""
        state: ConversationState = {
            "user_message": "天气怎么样",
            "current_user_id": "test-user",
            "intent": "unknown",
            "clarifying_question": "请问您想执行什么操作？",
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        assert "请问您想执行什么操作" in result["reply_message"]

    @pytest.mark.asyncio
    async def test_pre_set_reply_message(self) -> None:
        """测试 dispatch 已设置 reply_message 时不覆盖"""
        state: ConversationState = {
            "user_message": "筛选简历",
            "current_user_id": "test-user",
            "intent": "evaluate",
            "reply_message": "❌ 未找到匹配的岗位。",
            "errors": [],
        }

        with patch("app.services.conversation.nodes._get_db"):
            result = await feedback_node(state)

        # reply_message 已存在，feedback_node 应返回空 dict
        assert result == {}


class TestRouteByIntent:
    """route_by_intent 测试"""

    def test_evaluate_routes_to_dispatch(self) -> None:
        state: ConversationState = {"intent": "evaluate"}
        assert route_by_intent(state) == "dispatch"

    def test_help_routes_to_feedback(self) -> None:
        state: ConversationState = {"intent": "help"}
        assert route_by_intent(state) == "feedback"

    def test_unknown_routes_to_feedback(self) -> None:
        state: ConversationState = {"intent": "unknown"}
        assert route_by_intent(state) == "feedback"

    def test_default_routes_to_feedback(self) -> None:
        state: ConversationState = {}
        assert route_by_intent(state) == "feedback"
