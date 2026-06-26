"""Chat API 测试"""

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
        # Should get SSE stream with error event
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
    async def test_chat_returns_sse_stream(
        self,
        client: AsyncClient,
        auth_headers_recruiter: dict[str, str],
    ) -> None:
        """对话应返回 SSE 流"""
        # Mock the entire conversation graph to avoid real LLM calls
        mock_state = MagicMock()
        mock_state.values = {
            "reply_message": "✅ 测试回复",
            "reply_cards": None,
        }

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=aiter([]))
        mock_graph.aget_state = AsyncMock(return_value=mock_state)

        # build_conversation_graph is imported locally inside the function,
        # so we patch at the source module. Also mock get_checkpointer
        # and async_session to avoid real DB connections.
        with patch(
            "app.services.conversation.graph.build_conversation_graph",
            return_value=mock_graph,
        ), patch(
            "app.api.chat.get_checkpointer",
        ), patch(
            "app.api.chat.async_session",
        ):
            response = await client.post(
                "/api/chat/send",
                json={"message": "帮助"},
                headers=auth_headers_recruiter,
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
