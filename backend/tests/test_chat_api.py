"""Chat API 测试"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient

from app.schemas.chat import (
    JobListCard,
    JobDetailCard,
    FunnelCard,
    FunnelStage,
    CandidateListCard,
    CandidateItem,
    ConfirmCard,
    ResultEvent,
)


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

        # Mock async_session to return a proper async context manager
        # that provides a DB session with query results
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_async_session = MagicMock(return_value=mock_session_ctx)

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
            mock_async_session,
        ):
            response = await client.post(
                "/api/chat/send",
                json={"message": "帮助"},
                headers=auth_headers_recruiter,
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            # Should contain the session event as the first event
            assert "event: session" in response.text


class TestCardSerialization:
    """卡片序列化测试：验证所有卡片类型通过 SSE result 事件正确序列化"""

    def test_job_list_card_serialization(self) -> None:
        card = JobListCard(jobs=[{"job_code": "J04217", "title": "前端", "status": "active", "head_count": 3}])
        event = ResultEvent(reply_message="岗位列表", cards=[card])
        data = json.loads(event.model_dump_json())
        assert data["cards"][0]["type"] == "job_list"

    def test_funnel_card_serialization(self) -> None:
        card = FunnelCard(
            job_code="J04217",
            job_title="前端",
            stages=[FunnelStage(status="待审核", count=10, percentage=50.0)],
        )
        event = ResultEvent(reply_message="漏斗", cards=[card])
        data = json.loads(event.model_dump_json())
        assert data["cards"][0]["type"] == "funnel"

    def test_confirm_card_serialization(self) -> None:
        card = ConfirmCard(action="确认操作", params={"key": "value"})
        event = ResultEvent(reply_message="请确认", cards=[card])
        data = json.loads(event.model_dump_json())
        assert data["cards"][0]["type"] == "confirm"

    def test_mixed_card_types_serialization(self) -> None:
        """Mixed card types in a single ResultEvent"""
        cards: list = [
            JobListCard(jobs=[{"job_code": "J04217", "title": "前端", "status": "active", "head_count": 3}]),
            ConfirmCard(action="操作", params={}),
        ]
        event = ResultEvent(reply_message="混合卡片", cards=cards)
        data = json.loads(event.model_dump_json())
        assert len(data["cards"]) == 2
        assert data["cards"][0]["type"] == "job_list"
        assert data["cards"][1]["type"] == "confirm"

    def test_result_event_without_cards(self) -> None:
        event = ResultEvent(reply_message="无卡片")
        data = json.loads(event.model_dump_json())
        assert data.get("cards") is None
