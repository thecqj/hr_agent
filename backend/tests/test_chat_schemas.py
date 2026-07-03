"""Chat Card Schema 测试"""

from app.schemas.chat import (
    EvaluationSummaryCard,
    JobListCard,
    JobDetailCard,
    FunnelCard,
    CandidateListCard,
    ConfirmCard,
    ResultEvent,
)


class TestJobListCard:
    def test_create_job_list_card(self) -> None:
        card = JobListCard(
            jobs=[
                {"job_code": "J04217", "title": "前端开发", "status": "active", "head_count": 3},
                {"job_code": "J04218", "title": "产品经理", "status": "closed", "head_count": 1},
            ]
        )
        assert card.type == "job_list"
        assert len(card.jobs) == 2


class TestJobDetailCard:
    def test_create_job_detail_card(self) -> None:
        card = JobDetailCard(
            job={
                "job_code": "J04217",
                "title": "前端开发",
                "description": "负责前端开发",
                "requirements": "3年经验",
                "skills_required": ["React", "TypeScript"],
                "salary_min": 20000,
                "salary_max": 40000,
                "location": "北京",
                "work_type": "hybrid",
                "head_count": 3,
                "status": "active",
            }
        )
        assert card.type == "job_detail"


class TestFunnelCard:
    def test_create_funnel_card(self) -> None:
        card = FunnelCard(
            job_code="J04217",
            job_title="前端开发",
            stages=[
                {"status": "pending", "count": 10, "percentage": 50.0},
                {"status": "interview", "count": 5, "percentage": 25.0},
                {"status": "rejected", "count": 5, "percentage": 25.0},
            ]
        )
        assert card.type == "funnel"
        assert len(card.stages) == 3


class TestCandidateListCard:
    def test_create_candidate_list_card(self) -> None:
        card = CandidateListCard(
            job_code="J04217",
            job_title="前端开发",
            candidates=[
                {"name": "张三", "ai_score": 85.5, "ai_decision": "recommend", "status": "pending"},
                {"name": "李四", "ai_score": 72.0, "ai_decision": "recommend", "status": "interview"},
            ]
        )
        assert card.type == "candidate_list"
        assert len(card.candidates) == 2


class TestConfirmCard:
    def test_create_confirm_card(self) -> None:
        card = ConfirmCard(
            action="将候选人 张三 推进到面试阶段",
            params={"candidate_name": "张三", "target_status": "interview"},
        )
        assert card.type == "confirm"


class TestResultEvent:
    def test_result_event_reply_only(self) -> None:
        event = ResultEvent(reply_message="简单文本回复")
        assert event.reply_message == "简单文本回复"
        assert "cards" not in ResultEvent.model_fields
