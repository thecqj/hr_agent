"""LangGraph 节点单元测试"""

from typing import Any, cast

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.agent.nodes import (
    evaluate_node,
    screen_node,
    review_node,
)
from app.services.agent.state import EvaluationState
from app.schemas.agent import ResumeEvaluation, DimensionScore


# ── screen_node 测试 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_screen_node_with_quota() -> None:
    """有面试人数上限时，取 Top N"""
    state: EvaluationState = {
        "evaluation_results": [
            {"application_id": "a1", "weighted_total": 90, "suggestion": "recommend"},
            {"application_id": "a2", "weighted_total": 80, "suggestion": "recommend"},
            {"application_id": "a3", "weighted_total": 70, "suggestion": "neutral"},
            {"application_id": "a4", "weighted_total": 50, "suggestion": "reject"},
        ],
        "job_info": {"interview_quota": 2},
    }

    result = await screen_node(state, AsyncMock())

    screening = cast(dict[str, Any], result["screening_result"])
    assert len(screening["recommend_list"]) == 2
    assert len(screening["reject_list"]) == 2
    assert screening["recommend_list"][0]["application_id"] == "a1"
    assert screening["cutoff_score"] == 80


@pytest.mark.asyncio
async def test_screen_node_without_quota() -> None:
    """无面试人数上限时，按 60 分阈值划分"""
    state: EvaluationState = {
        "evaluation_results": [
            {"application_id": "a1", "weighted_total": 85, "suggestion": "recommend"},
            {"application_id": "a2", "weighted_total": 55, "suggestion": "reject"},
        ],
        "job_info": {"interview_quota": None},
    }

    result = await screen_node(state, AsyncMock())

    screening = cast(dict[str, Any], result["screening_result"])
    assert len(screening["recommend_list"]) == 1
    assert len(screening["reject_list"]) == 1
    assert screening["cutoff_score"] == 60.0


@pytest.mark.asyncio
async def test_screen_node_empty_results() -> None:
    """无评估结果时返回空列表"""
    state: EvaluationState = {
        "evaluation_results": [],
        "job_info": {},
    }

    result = await screen_node(state, AsyncMock())

    screening = cast(dict[str, Any], result["screening_result"])
    assert screening["recommend_list"] == []
    assert screening["reject_list"] == []
    assert screening["cutoff_score"] == 0.0


# ── evaluate_node 测试（Mock LLM）────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_node_success() -> None:
    """正常评估简历"""
    mock_evaluation = ResumeEvaluation(
        dimensions=[
            DimensionScore(name="技能匹配", score=85, weight=0.35, reason="匹配度高"),
            DimensionScore(name="经验相关性", score=70, weight=0.30, reason="3年经验"),
            DimensionScore(name="学历达标", score=90, weight=0.15, reason="985本科"),
            DimensionScore(name="综合印象", score=75, weight=0.20, reason="良好"),
        ],
        weighted_total=78.25,
        suggestion="recommend",
        summary="候选人技能匹配度高",
    )

    mock_provider = AsyncMock()
    mock_provider.evaluate_resume.return_value = mock_evaluation
    mock_provider.close = AsyncMock()

    mock_db = AsyncMock()
    mock_task = MagicMock()
    mock_db.get.return_value = mock_task

    state: EvaluationState = {
        "job_info": {"title": "前端工程师", "skills_required": ["React"]},
        "applications": [
            {
                "application_id": "app-1",
                "applicant_name": "张三",
                "structured_resume": {"name": "张三", "skills": ["React"]},
            }
        ],
        "task_id": "task-1",
        "errors": [],
        "evaluation_results": [],
        "evaluated_count": 0,
    }

    with patch("app.services.agent.nodes._get_llm_provider", return_value=mock_provider):
        with patch("app.services.agent.nodes.asyncio.sleep", new_callable=AsyncMock):
            result = await evaluate_node(state, mock_db)

    eval_results = cast(list[dict[str, Any]], result["evaluation_results"])
    assert len(eval_results) == 1
    assert eval_results[0]["application_id"] == "app-1"
    assert eval_results[0]["weighted_total"] == 78.25
    assert result["evaluated_count"] == 1


@pytest.mark.asyncio
async def test_evaluate_node_llm_failure_skips_resume() -> None:
    """LLM 评估失败时跳过该简历，继续下一份"""
    mock_provider = AsyncMock()
    # 第一次调用失败，第二次成功
    mock_provider.evaluate_resume.side_effect = [
        RuntimeError("API 调用失败"),
        ResumeEvaluation(
            dimensions=[DimensionScore(name="技能匹配", score=80, weight=1.0, reason="OK")],
            weighted_total=80.0,
            suggestion="recommend",
            summary="OK",
        ),
    ]
    mock_provider.close = AsyncMock()

    mock_db = AsyncMock()
    mock_task = MagicMock()
    mock_db.get.return_value = mock_task

    state: EvaluationState = {
        "job_info": {"title": "工程师"},
        "applications": [
            {"application_id": "app-1", "structured_resume": {"name": "A"}},
            {"application_id": "app-2", "structured_resume": {"name": "B"}},
        ],
        "task_id": "task-1",
        "errors": [],
        "evaluation_results": [],
        "evaluated_count": 0,
    }

    with patch("app.services.agent.nodes._get_llm_provider", return_value=mock_provider):
        with patch("app.services.agent.nodes.asyncio.sleep", new_callable=AsyncMock):
            result = await evaluate_node(state, mock_db)

    # 第一份跳过，第二份成功
    eval_results = cast(list[dict[str, Any]], result["evaluation_results"])
    assert len(eval_results) == 1
    assert eval_results[0]["application_id"] == "app-2"
    assert len(result["errors"]) == 1  # 第一份的错误被记录


# ── review_node 测试 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_review_node_no_borderline() -> None:
    """没有边界候选人时跳过复评"""
    state: EvaluationState = {
        "screening_result": {
            "recommend_list": [
                {"application_id": "a1", "weighted_total": 95},
            ],
            "reject_list": [
                {"application_id": "a2", "weighted_total": 30},
            ],
            "cutoff_score": 60.0,
        },
        "job_info": {},
        "errors": [],
    }

    result = await review_node(state, AsyncMock())

    assert result["review_adjustments"] == []


@pytest.mark.asyncio
async def test_review_node_with_borderline() -> None:
    """有边界候选人时调用 LLM 复评"""
    from app.schemas.agent import BorderlineReview

    mock_reviews = [
        BorderlineReview(
            application_id="a2",
            action="adjust",
            new_decision="recommend",
            reason="虽然分数略低但项目经验突出",
        ),
    ]
    mock_provider = AsyncMock()
    mock_provider.review_borderline.return_value = mock_reviews
    mock_provider.close = AsyncMock()

    # cutoff_score=60, borderline_range=10, so 50-70 are borderline
    state: EvaluationState = {
        "screening_result": {
            "recommend_list": [
                {
                    "application_id": "a1",
                    "weighted_total": 65,
                    "applicant_name": "X",
                    "suggestion": "recommend",
                    "evaluation": {"summary": "OK"},
                },
            ],
            "reject_list": [
                {
                    "application_id": "a2",
                    "weighted_total": 55,
                    "applicant_name": "Y",
                    "suggestion": "reject",
                    "evaluation": {"summary": "borderline"},
                },
            ],
            "cutoff_score": 60.0,
        },
        "job_info": {"title": "工程师"},
        "errors": [],
    }

    with patch("app.services.agent.nodes._get_llm_provider", return_value=mock_provider):
        result = await review_node(state, AsyncMock())

    adjustments = cast(list[dict[str, Any]], result["review_adjustments"])
    assert len(adjustments) == 1
    assert adjustments[0]["application_id"] == "a2"
    assert adjustments[0]["action"] == "adjust"


@pytest.mark.asyncio
async def test_review_node_failure_falls_back() -> None:
    """复评失败时沿用排序结果"""
    mock_provider = AsyncMock()
    mock_provider.review_borderline.side_effect = RuntimeError("API 错误")
    mock_provider.close = AsyncMock()

    # cutoff_score=60, borderline_range=10, so 50-70 are borderline
    state: EvaluationState = {
        "screening_result": {
            "recommend_list": [
                {
                    "application_id": "a1",
                    "weighted_total": 55,
                    "applicant_name": "X",
                    "suggestion": "recommend",
                    "evaluation": {"summary": "OK"},
                },
            ],
            "reject_list": [
                {
                    "application_id": "a2",
                    "weighted_total": 52,
                    "applicant_name": "Y",
                    "suggestion": "reject",
                    "evaluation": {"summary": "OK"},
                },
            ],
            "cutoff_score": 60.0,
        },
        "job_info": {},
        "errors": [],
    }

    with patch("app.services.agent.nodes._get_llm_provider", return_value=mock_provider):
        result = await review_node(state, AsyncMock())

    assert result["review_adjustments"] == []
    assert len(result["errors"]) == 1
    assert "边界复评失败" in result["errors"][0]
