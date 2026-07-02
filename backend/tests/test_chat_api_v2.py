"""Chat API 测试 — ReAct Agent 版本"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient


async def aiter(items: list[Any]) -> AsyncGenerator[Any, None]:
    """Helper: create an async iterator from a list"""
    for item in items:
        yield item


class TestChatSendEndpoint:
    """POST /api/chat/send 测试"""

    @pytest.mark.asyncio
    async def test_chat_requires_auth(self, client: AsyncClient) -> None:
        """未登录不能发送消息"""
        response = await client.post("/api/chat/send", json={"message": "测试"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_requires_recruiter(
        self,
        client: AsyncClient,
        auth_headers_seeker: dict[str, str],
    ) -> None:
        """求职者不能使用对话助手"""
        response = await client.post(
            "/api/chat/send",
            json={"message": "测试"},
            headers=auth_headers_seeker,
        )
        assert response.status_code == 200
        content = response.text
        assert "error" in content or "仅招聘者" in content

    @pytest.mark.asyncio
    async def test_chat_message_validation(
        self,
        client: AsyncClient,
        auth_headers_recruiter: dict[str, str],
    ) -> None:
        """消息不能为空"""
        response = await client.post(
            "/api/chat/send",
            json={"message": ""},
            headers=auth_headers_recruiter,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_returns_sse_stream_with_new_events(
        self,
        client: AsyncClient,
        auth_headers_recruiter: dict[str, str],
    ) -> None:
        """对话应返回 SSE 流，包含新事件类型"""
        mock_state = MagicMock()
        mock_state.values = {
            "messages": [MagicMock(type="ai", content="你好！", tool_calls=None)],
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=aiter([]))
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_async_session = MagicMock(return_value=mock_session_ctx)

        with patch(
            "app.services.conversation.graph.build_conversation_graph",
            return_value=mock_graph,
        ), patch(
            "app.api.chat.get_checkpointer",
        ), patch(
            "app.api.chat.async_session",
            mock_async_session,
        ):
            response = await client.post(
                "/api/chat/send",
                json={"message": "你好"},
                headers=auth_headers_recruiter,
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            assert "event: session" in response.text

    @pytest.mark.asyncio
    async def test_sse_no_thinking_or_intent_events(
        self,
        client: AsyncClient,
        auth_headers_recruiter: dict[str, str],
    ) -> None:
        """SSE 流不应包含 thinking 或 intent 事件"""
        mock_state = MagicMock()
        mock_state.values = {
            "messages": [MagicMock(type="ai", content="回复", tool_calls=None)],
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=aiter([]))
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_async_session = MagicMock(return_value=mock_session_ctx)

        with patch(
            "app.services.conversation.graph.build_conversation_graph",
            return_value=mock_graph,
        ), patch(
            "app.api.chat.get_checkpointer",
        ), patch(
            "app.api.chat.async_session",
            mock_async_session,
        ):
            response = await client.post(
                "/api/chat/send",
                json={"message": "测试"},
                headers=auth_headers_recruiter,
            )
            content = response.text
            assert "event: thinking" not in content
            assert "event: intent" not in content


class TestSSEEventSerialization:
    """SSE 事件序列化测试"""

    def test_tool_start_event_serialization(self) -> None:
        """tool_start 事件序列化"""
        from app.schemas.chat import ToolStartEvent

        event = ToolStartEvent(tool="query_jobs")
        data = json.loads(event.model_dump_json())
        assert data["tool"] == "query_jobs"

    def test_tool_end_event_serialization(self) -> None:
        """tool_end 事件序列化"""
        from app.schemas.chat import ToolEndEvent

        event = ToolEndEvent(tool="query_jobs")
        data = json.loads(event.model_dump_json())
        assert data["tool"] == "query_jobs"

    def test_text_delta_event_serialization(self) -> None:
        """text_delta 事件序列化"""
        from app.schemas.chat import TextDeltaEvent

        event = TextDeltaEvent(content="你好")
        data = json.loads(event.model_dump_json())
        assert data["content"] == "你好"

    def test_result_event_no_cards(self) -> None:
        """result 事件不再包含 cards"""
        from app.schemas.chat import ResultEvent

        event = ResultEvent(reply_message="测试回复")
        data = json.loads(event.model_dump_json())
        assert "cards" not in data
        assert data["reply_message"] == "测试回复"
