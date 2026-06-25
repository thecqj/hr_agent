from abc import ABC, abstractmethod

from app.schemas.agent import BorderlineReview, ResumeEvaluation


class BaseLLMProvider(ABC):
    """LLM 提供商统一接口"""

    @abstractmethod
    async def evaluate_resume(
        self,
        job_info: dict[str, object],
        structured_resume: dict[str, object],
        dimensions: list[str],
    ) -> ResumeEvaluation:
        """评估单份简历，返回结构化结果"""
        ...

    @abstractmethod
    async def review_borderline(
        self,
        job_info: dict[str, object],
        borderline_recommend: list[dict[str, object]],
        borderline_reject: list[dict[str, object]],
        cutoff_score: float,
    ) -> list[BorderlineReview]:
        """复评边界候选人"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """关闭提供商资源（如 HTTP 客户端）"""
        ...
